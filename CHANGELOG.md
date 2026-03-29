# Changelog

すべての注目すべき変更はここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システム「KabuSys」の基盤モジュール群を実装しました。主な追加点と設計上の注意点を以下に示します。

### Added
- パッケージエントリポイント
  - src/kabusys/__init__.py にパッケージ情報と __version__ = "0.1.0" を追加。公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動読み込み機能（OS 環境変数を保護して優先）。
    - .git または pyproject.toml を基準にプロジェクトルートを探索し、CWD に依存しない自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env の行パーサー強化（export プレフィックス対応、クォート内エスケープ、行末コメント処理の細かな仕様）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境（KABUSYS_ENV, LOG_LEVEL）などの設定プロパティとバリデーションを実装。
    - デフォルト値（KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を設定。

- AI 関連（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を実装。
    - タイムウィンドウ計算（calc_news_window）: 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して比較。
    - チャンク（最大 20 銘柄）で送信、1 銘柄あたり最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 再試行・指数バックオフ（429・ネットワーク断・タイムアウト・5xx に対応）。
    - レスポンス検証（JSON 抽出、results 配列、code と score の検証、スコアの ±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）と、DuckDB executemany の空リスト回避を考慮した実装。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
    - score_news: 書き込み銘柄数を返す。API 未設定時は ValueError。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - prices_daily から ma200_ratio を計算（ルックアヘッド防止のため target_date 未満のみ使用）。データ不足時は中立扱い（1.0）。
    - raw_news をマクロキーワードでフィルタしてタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を算出（記事がない場合は LLM 呼び出しを行わず 0.0 を採用）。
    - OpenAI 呼び出し用に独立した内部関数を持ち、retry / backoff を実装。API 失敗やパース失敗時は macro_sentiment=0.0 として続行（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックし例外を伝播。

- Research（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）算出を実装。
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装。データ不足時は None を返す挙動を明示。
    - calc_momentum / calc_volatility / calc_value が (date, code) をキーとする dict のリストを返す仕様。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（最小有効レコード数チェック等）。
    - ranking ユーティリティ（rank）: 同順位は平均ランクで扱う（丸めで ties 検出の安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
    - pandas 等への依存を排除。

- Data Platform（カレンダー、ETL、パイプライン）
  - src/kabusys/data/calendar_management.py
    - market_calendar に依存した営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録値が存在する場合は DB 値優先。NULL 値検出時に警告ログを出力してフォールバック。
    - calendar_update_job：J-Quants クライアント（jquants_client）から差分取得して market_calendar を更新する夜間バッチ処理。バックフィルと健全性チェック（未来日チェック）を実装。

  - src/kabusys/data/pipeline.py / etl.py
    - ETLResult データクラスを実装し公開（etl.py で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題・エラー概要などを保持し、辞書化メソッド to_dict を提供。
    - ETL パイプラインの補助ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - jquants_client と quality モジュールと連携する設計（差分更新、バックフィル、品質チェックの設計方針をコードドキュメントに明記）。

### Changed
- （初回リリースのため過去の変更はなし）  
  - 各モジュールに詳細な設計方針・安全策（ルックアヘッドバイアス回避、フェイルセーフ動作、DuckDB のバージョン差異対策など）をドキュメントとして取り入れています。

### Fixed
- （初回リリースのため過去の修正はなし）

### Notes / Implementation details / 注意点
- ルックアヘッドバイアス対策
  - AI / リサーチ機能はいずれも内部で datetime.today()/date.today() を直接参照せず、呼び出し元から target_date を受け取る設計です。DB クエリも target_date 未満／先を明示してルックアヘッドを防止しています。

- OpenAI 統合
  - gpt-4o-mini の JSON モードを使用。API 呼び出しは再試行・指数バックオフを実装し、5xx/429/タイムアウト等の扱いを明確化。API レスポンスのパース失敗時はスコアを 0.0（あるいは当該チャンクのスキップ）とするフェイルセーフを採用。

- DuckDB の互換性考慮
  - executemany に空リストを渡せないバージョン（DuckDB 0.10 など）への対処を実装（空チェックを行う）。
  - 日付型の取り扱いで safe な変換関数を提供。

- テスト容易性
  - OpenAI 呼び出しを隠蔽する内部関数は patch で差し替え可能（unittest.mock.patch など）。これによりユニットテストで外部 API をモックできます。

- ロギング
  - 各処理は適切な info/debug/warning/exception ログを出力するよう設計されています。

- 外部依存最小化
  - research の統計処理等は標準ライブラリのみで実装し、pandas などへの外部依存を避けています。

### Security
- 環境変数の自動読み込みは OS 環境変数を保護する仕組みを持ちますが、.env ファイルに機密情報を置く場合はファイルアクセス権等の運用上の注意が必要です。KABUSYS_DISABLE_AUTO_ENV_LOAD により CI/テスト時の自動読み込みを抑止できます。

今後の予定（例）
- strategy / execution / monitoring の具体的実装（現行はパッケージ公開のみ）。
- テストカバレッジ拡張、CI ワークフローおよび型注釈の追加チェック。
- OpenAI モデルやパラメータのチューニング、品質チェックルールの強化。

もし特定ファイルや機能についてより詳細な変更点（関数ごとの振る舞い、ログメッセージ、例外ハンドリング等）を求める場合は教えてください。必要に応じて個別の「変更履歴（ファイル別）」も作成します。