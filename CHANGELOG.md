# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  

- リリース日: 2026-04-09
- バージョンポリシー: SemVer 準拠（現行バージョン: 0.1.0）

## [0.1.0] - 2026-04-09

Added
- 初回公開（骨組み実装）: 日本株自動売買システム「KabuSys」の基本モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。
    - パブリックサブパッケージ: data, strategy, execution, monitoring をエクスポート。
  - 環境設定管理
    - src/kabusys/config.py
      - .env または環境変数から設定を読み込む自動ローダー実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
      - .env パーサーは export プレフィックス、クォート、エスケープ、インラインコメントに対応。
      - .env の読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書き防止。
      - Settings クラス（settings インスタンス）を提供し、J-Quants / kabu / LINE / DB / 監視 / システム設定等をプロパティで取得。
      - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など）や監視閾値（CPU/MEM/DISK）をサポート。
      - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
  - AI 周り（NLU / レジーム検出）
    - src/kabusys/ai/news_nlp.py
      - ニュース記事群を銘柄ごとに集約し OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信、センチメント（ai_score）を ai_scores テーブルへ書き込む。
      - ニュース収集ウィンドウ計算（calc_news_window）を提供（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
      - バッチサイズやトリム（記事数・文字数制限）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
      - API 応答の堅牢なバリデーション（JSON 取り出し、results リスト、各要素の code/score 検証、スコアのクリップ）を実装。
      - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）を実装。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225連動型）200日移動平均乖離（70%）とニュース由来の LLM マクロセンチメント（30%）を合成し、日次で市場レジーム（bull/neutral/bear）を決定。
      - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、合成スコア計算、market_regime テーブルへの冪等書き込みを実装。
      - OpenAI 呼び出し失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフを採用。
      - レトライ・バックオフ、API レスポンス JSON パースの安全処理を実装。
  - Data / ETL / カレンダー / パイプライン
    - src/kabusys/data/pipeline.py
      - ETLResult データクラスを追加（ETL 実行結果、品質チェック結果・エラー集約・シリアライズ機能）。
      - 差分更新・バックフィル（デフォルト再取得日数）・品質チェックを想定した設計（実装の骨子）。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を公開インターフェースとして再エクスポート。
    - src/kabusys/data/calendar_management.py
      - market_calendar テーブルに基づく営業日ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar が未取得のときは曜日ベースでフォールバック（土日非営業）。
      - calendar_update_job: J-Quants から差分取得し冪等に保存する夜間バッチジョブ、バックフィル / 健全性チェックを実装。
    - DuckDB を主要ローカル DB として利用する SQL 実装群（すべて DuckDB 接続を受け取る設計）。
  - Research（因子・特徴量探索）
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value を実装（モメンタム／ボラティリティ／バリュー指標）。
      - 各関数は prices_daily / raw_financials を参照し、(date, code) キーの辞書リストを返す設計。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関）、rank、factor_summary（基本統計）を実装。
    - src/kabusys/research/__init__.py で主要関数を再エクスポート。
  - utils / 実装方針（横断的）
    - ルックアヘッドバイアス対策: datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）。
    - DB 書き込みは冪等化を重視（DELETE→INSERT、ON CONFLICT 等の設計を想定）。
    - OpenAI との連携は JSON Mode を使い厳密な JSON 出力を想定、かつレスポンスの堅牢なパースとエラーハンドリングを実装。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え（mock）可能な内部関数を用意。
    - DuckDB バージョン互換性（executemany の空リスト回避など）に配慮した実装。

Fixed
- フェイルセーフ動作の明確化:
  - OpenAI API 呼び出しの失敗、JSON パースエラー、非期待ステータスコード等は例外をそのまま上位へ投げず、ログ出力のうえ安全なデフォルト（news_nlp: スコア未取得扱い / regime_detector: macro_sentiment=0.0）で継続する設計を採用。
- .env パーサーの堅牢化:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント扱い（クォートなしでは '#' の扱いを区別）などを正確化。
- DuckDB 書き込み周りの互換性対応:
  - DuckDB 0.10 の executemany の制約（空リスト禁止）を避けるため、params の存在チェックを入れてから executemany を呼ぶ実装に。

Changed
- （該当なし）初回リリースのため破壊的変更は無し。

Security
- 環境変数の扱いに注意:
  - OS 環境変数は .env による上書きを基本的に防止（protected set）する仕様を導入。
  - OpenAI API キー未設定時は明示的に ValueError を投げ、キー漏洩や誤設定の早期検出を促す。

Notes / Developer hints
- OpenAI のモデルは現状 gpt-4o-mini を使用する設計（news_nlp / regime_detector）。
- API 呼び出しのテストは内部の _call_openai_api を unittest.mock.patch 等で差し替えて行うことを想定。
- settings（kabusys.config.settings）経由で各種パス（duckdb/sqlite/paper sqlite）、API トークン、挙動フラグを取得可能。
- ETL / calendar / research / ai いずれも DuckDB 接続を受け取り副作用は DB への書き込みに限定する想定。これにより本番発注ロジックと分離され安全にロジック検証が可能。

今後の予定（短期的ロードマップの例）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジックと発注実装の追加。
- 単体テスト・統合テスト、CI ワークフローの整備。
- パフォーマンス最適化（ETL の差分取得アルゴリズム、DB インデックス化等）。
- モデル運用とコスト最適化（OpenAI 呼び出しのバッチ調整、キャッシュ機構の導入）。

-- 
この CHANGELOG は現行ソースコードから推測して作成しています。実際のリリースノートや変更履歴を作成する際は、コミット履歴や PR の説明と照合してください。