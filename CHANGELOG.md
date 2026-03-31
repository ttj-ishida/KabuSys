# CHANGELOG

すべての注目すべき変更を記録します。形式は「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-31

初期リリース。日本株自動売買／データ基盤／リサーチ／AIユーティリティ群を提供するパッケージのベース実装を公開。

### Added
- パッケージメタ情報
  - パッケージバージョンを設定: kabusys.__version__ = "0.1.0"
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (kabusys.config)
  - .env 自動読み込み実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサを堅牢化:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート処理（バックスラッシュエスケープ対応）およびインラインコメント処理
    - キーが空・無効行は無視
  - _load_env_file による protected keys（OS 環境変数保護）と override オプション。
  - Settings クラスで各種設定をプロパティとして公開:
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / システム設定（env, log_level）など
    - 必須値取得時の検証（未設定時は ValueError）
    - KABUSYS_ENV と LOG_LEVEL の許容値検証と便利な is_live / is_paper / is_dev プロパティ
    - デフォルト DB パス等の合理的なデフォルト値（duckdb/sqlite/pid ファイル等）

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を入力に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄別センチメントを取得。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり最大記事数・文字数トリムの実装。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）への指数バックオフ。
    - レスポンスの頑健なバリデーション（JSON モードでも前後ノイズを復元）、スコアの ±1.0 クリップ。
    - 部分成功時に既存の他銘柄スコアを保護するための「削除 → 挿入」方式での冪等書き込み。
    - テスト容易性を考慮し、API 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
    - 時間ウィンドウ計算（JST 前日15:00〜当日08:30 を UTC に変換）を calc_news_window として提供。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - ma200_ratio の算出（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロ記事の抽出はキーワードベース（定義済みマクロキーワードリスト）で最大 20 件取得。
    - OpenAI 呼び出し（gpt-4o-mini, JSON Mode）と冗長なリトライ・エラーハンドリング（5xxはリトライ、その他はフォールバック）。
    - API 未設定時は明示的な ValueError を送出。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK を試行）。
    - フェイルセーフ: API 失敗やデータ不足時は macro_sentiment=0.0、ma200_ratio が不十分な場合は中立 1.0 を使用。

- Data / ETL / カレンダー管理 (kabusys.data)
  - ETL インターフェース (kabusys.data.pipeline / ETLResult)
    - ETL 実行結果を表す dataclass (ETLResult) を追加（品質問題・エラー集約・to_dict 等）。
    - 差分取得・バックフィル・品質チェックの設計方針に沿ったユーティリティを実装（ETLResult による結果集約）。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー取得・夜間バッチ更新 job (calendar_update_job)。
    - market_calendar を参照した営業日判定・next/prev_trading_day・get_trading_days・is_sq_day の実装。
    - DB がまばらな場合の曜日ベースフォールバック、最大探索日数制限による安全性、バックフィル期間の取り込み、健全性チェック。
    - jquants_client 経由での取得/保存呼び出しを想定（fetch/save の例外を捕捉して安全に終了）。

- Research / ファクター計算 (kabusys.research)
  - ファクター計算モジュール (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（true range の取扱いに注意）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS = 0/欠損時は None）。
    - DuckDB を用いた SQL 中心の実装、外部 API 非依存、結果は dict リスト形式で返す。
  - 特徴量探索モジュール (feature_exploration)
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を効率的に取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数チェック）。
    - rank: 同順位を平均ランクで扱うランク付けユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
    - すべて標準ライブラリ（pandas 非依存）で実装。

- パッケージ内のテスト・差し替えフック
  - OpenAI 呼び出しや内部処理（_call_openai_api など）を patch しやすいように設計し、ユニットテストでの差し替えを想定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キー・機密情報の取り扱いについて
  - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で指定する必要がある（未指定時は ValueError）。
  - .env 読み込みは protected keys を使って OS 環境変数を上書きから保護。
  - 本リリースでは機密情報の暗号化保管等は含まれていないため、運用時は環境変数管理に注意。

### Known limitations / 注意事項
- DB スキーマ依存
  - 多くの関数は DuckDB の特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）を前提とする。事前にスキーマとデータ投入が必要。
- ルックアヘッド防止
  - 設計上、datetime.today() / date.today() を直接参照しないようにしている関数が多い（テスト時は明示的に target_date を渡す必要あり）。
- フェイルセーフ挙動
  - LLM / API 呼び出し失敗時は基本的に例外を投げずフォールバック（0.0 等）して処理を継続する設計。重大なエラーはログに記録されるが、部分失敗を考慮した書き込み戦略を採用。
- OpenAI SDK 互換性
  - OpenAI の SDK 仕様変化に備えてエラーオブジェクトの属性アクセスを安全に行う実装をしているが、将来の SDK 変更による影響には注意。

---

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現時点ではパッケージ公開のみ）
- テストカバレッジ拡充・CI 組み込み
- ドキュメント（Usage / デプロイ手順 / DB スキーマ）の整備

（注）本 CHANGELOG はソースコードの内容に基づき推測して作成しています。追加の変更履歴やリリースノートがある場合は追記してください。