Keep a Changelog に準拠した変更履歴

すべての重要な変更はこのファイルに記載します。  
フォーマットの詳細は https://keepachangelog.com/ja/ を参照してください。

Unreleased
---------
（なし）

0.1.0 - 2026-04-09
-----------------
初回リリース

Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API（パッケージトップ）は data, strategy, execution, monitoring を想定。
  - バージョン情報を src/kabusys/__init__.py にて管理（__version__ = "0.1.0"）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装（読み込み優先度: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）。これによりカレントワーキングディレクトリに依存せず動作。
  - 自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - .env の行パーサーを強化（export 形式対応、クォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - 読み込み時の上書き制御（override, protected）を実装し、OS 環境変数を保護。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB / Paper Trading / 監視 / システム設定（KABUSYS_ENV, LOG_LEVEL 等）をプロパティ経由で取得。バリデーション（列挙値チェック、数値変換等）を実装。
  - Paper Trading の挙動（PAPER_FILL_MODE）や Paper 用 DB パス等を設定可能に。

- AI 関連（src/kabusys/ai/）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄単位に記事を結合し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算。
    - 時刻ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST、DB 比較は UTC）を計算するユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数上限・文字数トリム、JSON Mode を使った厳格なレスポンス検証を実装。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ）、レスポンス検証失敗や API エラーはフェイルセーフでスキップ（例外は伝播させない）。
    - レスポンス内 JSON 抽出の耐性（前後余計なテキストを含む場合の {} 抽出）やスコアクリップ（±1.0）。
    - DB への書き込みは部分失敗を避けるため「取得済みコードのみを DELETE → INSERT」で置換（トランザクション利用、ROLLBACK のハンドリング）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio とマクロニュースを取得し、OpenAI で macro_sentiment を取得（記事なしの場合は LLM 呼び出しをスキップ、API 失敗時は 0.0 にフォールバック）。
    - レジームスコア合成、閾値に基づくラベル付け、market_regime テーブルへ冪等的に書き込み（DELETE→INSERT を含むトランザクション）。
    - API 呼び出しや JSON パース失敗時のフェイルセーフ、リトライロジック、テスト差し替えポイントを実装。
    - lookahead バイアスを防ぐ設計（内部で datetime.today()/date.today() を参照しない。対象日は呼び出し元から渡す）。

- データプラットフォーム（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダー取得用の夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 営業日判定ユーティリティ群を提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未取得の場合は曜日ベース（週末除外）で一貫したフォールバックを行う。最大探索日数を設定して無限ループを防止。
    - DB 値優先の一貫した挙動（登録ありは DB を優先、未登録日は曜日フォールバック）。

  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得・保存・品質チェックを行う設計方針を実装（J-Quants クライアント呼び出し、バックフィル、品質チェックの集計方針）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - jquants_client / quality 等のクライアント・モジュールと連携する設計（jquants_client を想定）。

- リサーチ（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR, ATR 比率）、Value（PER, ROE）等の計算関数を追加。
    - DuckDB の SQL ウィンドウ関数を利用して効率的に計算。入力は prices_daily / raw_financials のみで外部 API には依存しない。
    - データ不足時の None ハンドリング（例: MA200 行数不足で ma200_dev を None にする）。
    - 出力は (date, code) を含む dict のリストとして返却。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン、horizons バリデーション、単一クエリでの取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman ランク相関、None/有限値除外、有効レコード数が少ない場合は None）。
    - ランク関数 rank（同順位の平均ランク、丸め処理で浮動小数の ties を扱う）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算、None 値除外）。

Changed
- （初回リリースのため過去リリースとの差分はなし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数取り扱いに関する注意: .env 読み込みで OS 環境変数を保護する仕組みを導入。ただし機密情報は適切にアクセス管理された環境で設定してください（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス防止:
  - AI/スコアリング/レジーム判定/ETL/リサーチ処理は内部で datetime.today() / date.today() を参照しない設計。対象日を外部から明示的に渡すことで、将来データ参照（ルックアヘッド）を防止。
- フェイルセーフ:
  - OpenAI 等の外部 API 呼び出しで失敗した場合でもシステム全体が停止しないように、スコアのフォールバックや該当チャンクのスキップを採用。
- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api 等）はテスト時に差し替え可能に実装（unittest.mock.patch 推奨）。
- DB 書き込み:
  - 各書き込み処理は冪等化（DELETE→INSERT や ON CONFLICT 相当）を考慮しトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK に失敗した場合のログ出力も実装。

互換性（Breaking Changes）
- 初回リリースのため過去バージョンとの互換性問題はありません。

既知の制限 / TODO（今後の改善候補）
- 一部機能は jquants_client / kabu ステーション連携や具体的な保存ロジックに依存しており、実行環境のセットアップ（DuckDB スキーマ、.env 設定、OpenAI API キー等）が必要。
- 現時点で PBR・配当利回り等のバリューファクターは未実装（calc_value の注記参照）。
- DuckDB バインドの互換性（executemany の空リスト扱い等）に関する注意書きを実装済み。将来の DuckDB バージョンで挙動差が出る可能性あり。

作者
- kabusys 開発チーム

----- 
注: 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートやバージョン管理履歴（git のコミットログ等）がある場合は、それを優先してください。