# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のリリース方針: 初回公開リリースを v0.1.0 として記録します。

## [0.1.0] - 2026-03-26

### Added
- 初期リリース: KabuSys — 日本株自動売買/データ基盤・リサーチ用ライブラリを追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パブリックサブパッケージ: data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途向け）。
  - .env 読み込み優先順位: OS 環境変数 > .env.local > .env。`.env.local` は既存環境変数を上書き可能（ただし OS の既存キーは保護）。
  - .env パーサは以下に対応:
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなしの行では `#` 前のスペース/タブをコメントと判別
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - 任意・デフォルト: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）
    - 環境（KABUSYS_ENV）検証: 有効な値は development / paper_trading / live
    - LOG_LEVEL 検証: DEBUG / INFO / WARNING / ERROR / CRITICAL
    - ヘルパープロパティ: is_live / is_paper / is_dev

- ニュースNLP（AI）モジュール（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols から銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
  - 特徴:
    - ニュースウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST を内部で UTC に変換して使用（calc_news_window）
    - 1チャンクあたり最大 20 銘柄（_BATCH_SIZE）、1銘柄あたり最新 10 記事・最大 3000 文字でトリム
    - API リトライ: 429（RateLimit）・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ（最大設定あり）
    - レスポンスの堅牢なバリデーション: JSON 抽出（余分な前後テキストが混入した場合も復元を試みる）、results リスト・各要素の code/score を検証
    - スコアは ±1.0 にクリップ
    - 書込みは idempotent に実施（対象コードのみを DELETE → INSERT）し、部分失敗時に他コードの既存スコアを保護
    - DuckDB 互換性対応: executemany に空リストを与えないガード
    - テスト用フック: _call_openai_api を patch して差し替え可能（モック容易性を考慮）

- 市場レジーム判定（AI）モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
  - 処理詳細:
    - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立（1.0）。
    - マクロニュースは news_nlp の calc_news_window を利用してウィンドウ抽出し、OpenAI（gpt-4o-mini）で JSON 出力（{"macro_sentiment": 0.0}）を期待
    - API 失敗時は macro_sentiment = 0.0 をフォールバック（例外にせず継続）
    - 合成スコアは clip され、閾値により regime_label を決定
    - market_regime テーブルへの書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等的に行う
    - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定の場合は ValueError を送出

- リサーチ（ファクター計算・特徴量探索）モジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足なら None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。データ不足時は None。
    - calc_value: raw_financials から最新財務を取得して PER・ROE を計算（EPS が 0/欠損なら PER は None）。
    - 実装は DuckDB 上の SQL（ウィンドウ関数等）を利用し、外部 API に依存しない。
  - feature_exploration.py:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って算出。horizons のバリデーションあり。
    - calc_ic: スピアマン（ランク相関）による IC 計算、3 件未満で None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を算出。
  - research パッケージは主要関数と zscore_normalize を再エクスポート。

- データ基盤モジュール（src/kabusys/data/*）
  - calendar_management.py:
    - JPX カレンダーの管理機能（market_calendar テーブル）を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベース（平日）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を保存（バックフィル・健全性チェックあり）。
    - 最大探索日数、バックフィル日数、先読み日数などの定数を定義して安全に動作。
  - pipeline.py:
    - ETL パイプライン用ユーティリティと ETLResult データクラスを提供。
    - ETLResult: ETL 実行結果の構造化（取得数・保存数・quality_issues・errors 等）と to_dict メソッドを実装。
    - 差分更新、バックフィル、品質チェック（quality モジュール利用）方針をドキュメント化。
    - DuckDB のテーブル存在確認・最大日付取得ユーティリティを実装。
  - etl.py:
    - ETLResult を再エクスポート。

- jquants_client や quality など外部接続クライアントは data パッケージ下で利用する想定（実装は別モジュールで注入）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種機密は環境変数経由で必ず取得する設計。必須のキーが未設定の場合は ValueError を投げ、明示的に通知するようにしている。

### Notes / Usage & Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY は news / regime 機能を使う際に必要（関数に api_key を直接渡すことも可能）。
- 自動 .env ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで .env 読み込みを抑制する用途等）。
- DuckDB / SQLite ファイルのデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - 必要に応じて環境変数で上書き可能。
- OpenAI 呼び出し部分はテスト容易性を考え、内部の _call_openai_api をモック可能（unittest.mock.patch を利用）に実装。
- 日付処理:
  - どの AI / スコア算出関数も内部で datetime.today()/date.today() を参照せず、呼び出し側から target_date を渡す方式を採用。これによりルックアヘッドバイアスを防止。

### Known limitations / TODO
- PBR・配当利回りなどの一部バリューファクターは現バージョンでは未実装（calc_value 参照）。
- news_nlp / regime_detector は gpt-4o-mini の JSON mode に依存しており、API 側の挙動変化に対してリトライやパースフォールバックを備えているが、期待された JSON レスポンスを常に保証するものではない。
- jquants_client / kabu API クライアントの具象実装はこのコードベースで注入して利用する想定（外部モジュール）。

---

今後のリリースでは、バグ修正・パフォーマンス改善・追加ファクター・より多様な出力フォーマット対応等を予定しています。フィードバックや不具合報告は issue にてお知らせください。