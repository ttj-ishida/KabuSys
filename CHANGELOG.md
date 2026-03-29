# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース

### Added
- パッケージ基本
  - パッケージのバージョン情報と公開 API を `src/kabusys/__init__.py` に追加（`__version__ = "0.1.0"`）。
- 設定・環境変数管理（`kabusys.config`）
  - プロジェクトルート（`.git` または `pyproject.toml`）を基に `.env`/.env.local を自動検出して読み込む機能を実装。カレントワーキングディレクトリに依存せずパッケージ配布後も動作するよう設計。
  - `.env` 行パーサの強化：`export KEY=val` 形式、クォート（シングル／ダブル）内のエスケープ、インラインコメントの処理を考慮した安全なパース実装（`_parse_env_line`）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - OS 環境変数を保護するための `protected` キーセットを用いた上書き制御、`.env.local` による優先上書き処理を実装（`_load_env_file`）。
  - 必須設定アクセス用の `Settings` クラスを提供（例：`jquants_refresh_token`, `kabu_api_password`, `slack_bot_token` 等）、デフォルト値やバリデーション（`KABUSYS_ENV`, `LOG_LEVEL` の許容値チェック）を実装。
  - データベースパスの Path 化 (`duckdb_path`, `sqlite_path`) を実装。
- データ処理・ETL（`kabusys.data`）
  - ETL パイプラインの結果を保持する `ETLResult` データクラスを実装し、`kabusys.data.etl` で再エクスポート。
  - 市場カレンダー管理モジュールを実装（`calendar_management.py`）。JPX カレンダーの夜間差分更新ジョブ、営業日判定（`is_trading_day` / `next_trading_day` / `prev_trading_day` / `get_trading_days` / `is_sq_day`）を提供。
  - calendar バッチ処理（`calendar_update_job`）は J-Quants クライアント経由で差分取得し冪等保存を行う実装。
  - DuckDB 互換性を考慮したユーティリティ（テーブル存在確認・日付変換等）を実装。
  - ETL パイプラインのユーティリティ（差分取得、保存、品質チェック連携）設計を追加（`pipeline.py`）。
- 研究用ユーティリティ（`kabusys.research`）
  - ファクター計算モジュール（`factor_research.py`）を実装：
    - モメンタム（1M/3M/6M）、200日移動平均乖離（`calc_momentum`）。
    - ボラティリティ / 流動性（20日 ATR、相対ATR、平均売買代金、出来高比率）（`calc_volatility`）。
    - バリュー（PER, ROE、raw_financials からの最新財務取得）（`calc_value`）。
  - 特徴量探索モジュール（`feature_exploration.py`）を実装：
    - 将来リターン計算（任意ホライズン、`calc_forward_returns`）。
    - IC（Spearman のランク相関）計算（`calc_ic`）。
    - ランク関数（同順位は平均ランク、`rank`）。
    - ファクター統計サマリ（count/mean/std/min/max/median、`factor_summary`）。
  - 研究ユーティリティをまとめて公開（`__all__` の設定）。
- AI / NLP（`kabusys.ai`）
  - ニュース NLP スコアリング（`news_nlp.py`）を実装：
    - 前日 15:00 JST ～ 当日 08:30 JST に相当する UTC ウィンドウ計算（`calc_news_window`）。
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、最大文字数・記事数でトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ、チャンク処理、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーション、スコアの ±1.0 クリップを実装。
    - DuckDB の executemany に対する空リストガード実装（互換性確保）。
    - `score_news` は取得した銘柄数を返却。
    - テスト容易性のため `_call_openai_api` を patch 可能に設計。
  - 市場レジーム判定（`regime_detector.py`）を実装：
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（`bull`/`neutral`/`bear`）を算出。
    - マクロセンチメントはマクロキーワードでフィルタした記事タイトルを LLM に渡して JSON レスポンス（{"macro_sentiment": float}）を受け取る方式。
    - API リトライ（429, ネットワーク, タイムアウト, 5xx）とフォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム結果は冪等に `market_regime` テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止のため内部で `datetime.today()` 等を参照しない設計。
  - ai パッケージの公開関数（`score_news`, `score_regime` など）を `__all__` で管理。
- ロギングと堅牢性
  - 各モジュールで詳細なログメッセージを追加（INFO/WARNING/DEBUG レベル）。
  - API レスポンスパース失敗や DB ロールバック失敗等の例外をキャッチしてログに記録、必要に応じて安全なフォールバックを行う実装。

### Changed
- （初回リリースのため該当なし）: 将来の変更時に Breaking Change の注記を行う予定。

### Fixed
- 環境変数パースと読み込みの強化により、`.env` の特殊ケース（クォート内のエスケープ、インラインコメント、`export` プレフィックス）を正しく処理するよう改善。
- DuckDB 特有の制約（executemany に空リスト不可、リスト型バインドの不安定性）を回避するための対処を実装（`score_news` の DELETE/INSERT ロジック等）。
- OpenAI レスポンスの JSON モードでも前後に余計なテキストが混入する場合に備え、最外の `{...}` を抽出して復元する処理を追加（JSON パース耐性向上）。

### Security
- OpenAI API キー未設定時に明確な `ValueError` を発生させることで不正な API 呼び出しを防止（`score_news`, `score_regime`）。
- 環境変数の自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` により無効化可能（テスト環境や CI での誤動作防止）。
- OS 環境変数を保護する仕組みを導入（`.env` 読み込み時の `protected` set）。

### Notes / Implementation details
- ルックアヘッドバイアス防止: AI モジュール・研究モジュールのいずれも `date`/`target_date` を明示的に受け取り、内部で `date.today()` を参照しない設計。過去データのみを使用することを明示。
- DuckDB の日付値は `date` 型に変換して扱うユーティリティを提供。
- J-Quants クライアント（`kabusys.data.jquants_client`）を介して外部 API を呼び出す想定。実際の API 呼び出し部分は同クライアント実装に依存。
- テストしやすさを考慮し、OpenAI 呼び出しの内部関数を patch 可能に実装（ユニットテストでのモック容易化）。

（将来的なリリースでは、各モジュールごとにより細かいリリースノート（バグフィックス / 互換性破壊の有無 / パフォーマンス改善等）を追記します。）