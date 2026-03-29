# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

<!-- 開発中の変更点はここに記載 -->

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。日本株の自動売買・データ基盤・リサーチ用ユーティリティ群を提供。
- パッケージ全体
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。
  - 公開モジュール群: `data`, `strategy`, `execution`, `monitoring`（__all__ に含む）。
- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に __file__ を起点に探索（配布後の動作を考慮）。
  - .env パーサ: `export KEY=val`、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメントの取り扱いに対応。
  - オーバーライド挙動と protected keys（OS 環境の保護）を考慮したファイル読み込み実装。
  - Settings クラスで主要設定をプロパティとして公開:
    - J-Quants / kabu API / Slack / DB パス等: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト http://localhost:18080/kabusapi）, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `DUCKDB_PATH`（デフォルト data/kabusys.duckdb）, `SQLITE_PATH`（デフォルト data/monitoring.db）。
    - 実行環境: `KABUSYS_ENV`（有効値: `development`, `paper_trading`, `live`）と `LOG_LEVEL`（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）。環境値検証を行い不正値は ValueError を送出。
    - ヘルパープロパティ: `is_live`, `is_paper`, `is_dev`。
- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを計算。
    - ニュース収集ウィンドウ: JST 基準で「前日 15:00 JST ～ 当日 08:30 JST」を UTC naive datetime に変換して扱う（`calc_news_window`）。
    - バッチサイズ: 最大 20 銘柄 / API コール。1銘柄あたり最大 10 記事・3000 文字にトリム。
    - API リトライ仕様: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフ（最大リトライ回数設定）。
    - レスポンス検証: JSON 抽出、`results` リスト構造、各要素の `code` と `score` を検証。数値化・有限性チェックあり。スコアは ±1.0 にクリップ。
    - データベース書き込み: 成功した銘柄のみを対象に DELETE → INSERT の形で idempotent に ai_scores テーブルへ保存（部分失敗時に既存データを保護）。
    - フェイルセーフ: API 失敗/パース失敗時は該当チャンクをスキップし処理継続。OpenAI 呼び出しの差し替え用フック（テスト用の patch）を用意。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して、日次の市場レジーム（`bull` / `neutral` / `bear`）を判定するロジックを提供。
    - MA 計算: 直近 200 日データ（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - マクロ記事取得: raw_news からマクロキーワード（デフォルトリストあり）でフィルタし最大 20 記事を取得。
    - LLM 呼び出し: gpt-4o-mini を用い JSON レスポンスを期待。API 障害時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - スコア合成と閾値: 重み付け合成、スコアを -1.0〜1.0 にクリップ。閾値 `_BULL_THRESHOLD = 0.2`, `_BEAR_THRESHOLD = 0.2`。
    - DB 書き込み: market_regime テーブルへ BEGIN / DELETE / INSERT / COMMIT の冪等書き込みを行う。失敗時は ROLLBACK を試行して例外を上位へ伝搬。
- リサーチモジュール (`kabusys.research`)
  - factor_research:
    - モメンタム (`calc_momentum`): 1M/3M/6M リターン、200日 MA 乖離の算出。データ不足時は None を返す。
    - ボラティリティ / 流動性 (`calc_volatility`): 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - バリュー (`calc_value`): raw_financials から EPS/ROE を参照し PER/ROE を算出。EPS が 0 または欠損の場合は None。
    - 設計上、prices_daily / raw_financials のみを参照し本番口座や発注 API へのアクセスはしない。
  - feature_exploration:
    - 将来リターン計算 (`calc_forward_returns`): 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - IC（Information Coefficient）計算 (`calc_ic`): スピアマンのランク相関を算出（有効レコード数 3 未満で None）。
    - 統計サマリー (`factor_summary`): count/mean/std/min/max/median を計算。
    - ユーティリティ: `rank`（同順位は平均ランク）。
  - `kabusys.research` パッケージは zscore_normalize（`kabusys.data.stats` 由来）などを再エクスポート。
- データモジュール (`kabusys.data`)
  - カレンダー管理 (`calendar_management`)
    - JPX 市場カレンダー管理。営業日判定ユーティリティ群:
      - `is_trading_day(conn, d)`, `next_trading_day(conn, d)`, `prev_trading_day(conn, d)`, `get_trading_days(conn, s, e)`, `is_sq_day(conn, d)` を提供。
    - DB にカレンダーがある場合は DB 値を優先。未登録日は曜日（平日）ベースでフォールバックする設計により、まばらな DB データでも一貫した判定を実現。
    - next/prev 関数は最大探索日数 `_MAX_SEARCH_DAYS`（デフォルト 60）で探索し、超過時は ValueError を送出。
    - 夜間更新ジョブ (`calendar_update_job`)：J-Quants API から差分取得 → `jquants_client.save_market_calendar` による idempotent 保存。バックフィル日数と健全性チェックを実装。
  - ETL / パイプライン (`pipeline`, `etl`)
    - ETLResult データクラスを実装し、ETL の取得件数・保存件数・品質問題・エラーの集約を行う。`to_dict()` でシリアライズ可能。
    - 差分更新・バックフィル・品質チェック（`kabusys.data.quality` 想定）を行う設計。最小データ日 `_MIN_DATA_DATE`、カレンダー先読み等の定数を定義。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得などを提供。
    - `kabusys.data.etl` は `ETLResult` を公開再エクスポート。
- DuckDB をメインの組み込み DB として利用する設計。SQL + Python でファクター計算や ETL を実行。
- テスト支援
  - OpenAI 呼び出し箇所は内部関数 `_call_openai_api` を用意し、ユニットテストで patch して差し替え可能にしている。

### Security
- 設定読み込み時、OS 環境変数はデフォルトで保護され上書きされない仕組みを採用（.env ロード時の protected keys）。
- 必須の機密情報（OpenAI API キー、Slack トークン、J-Quants リフレッシュトークン、kabu API パスワード等）は Settings のプロパティで要求し、未設定時は ValueError を送出することで誤設定を明示。

### Notes / Design decisions
- ルックアヘッドバイアス回避:
  - AI 及び計算モジュールは内部で datetime.today() / date.today() を直接参照しない（外から target_date を注入する設計）。
  - DB クエリは target_date 未満または指定のウィンドウでデータを限定。
- API 呼び出しの堅牢性:
  - LLM 呼び出しは 429 / 接続エラー / タイムアウト / 5xx に対してリトライ・バックオフを実装。致命的でないエラーはスキップして処理を継続するフェイルセーフ方針を採用。
- DB 書き込みは可能な限り冪等（DELETE→INSERT / ON CONFLICT 想定）にしており、部分失敗時に既存の有効データを保護する実装を行っている。
- ニュース時間ウィンドウは JST で定義し、DB 側の UTC タイムスタンプと照合するために明示的に UTC naive datetime を計算する（calc_news_window）。
- OpenAI SDK 依存部分は抽象化されており、将来の SDK 変更に備えてエラーオブジェクトの属性参照は堅牢に実装している（例: getattr で status_code を取得）。

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

## 今後の予定（参考）
- ファクター正規化やポートフォリオ構築ロジックの追加。
- モニタリング・アラート機能の拡充（Slack 通知等の統合）。
- より多様な外部データソース（J-Quants 以外）のサポート。
- OpenAI 呼び出しのロギング/監査と消費トークンの可視化。

---

注: 本 CHANGELOG は提供されたコードベースの実装内容と docstring から推測して作成しています。実運用時は実際のリリース日、変更差分、互換性情報を確定してから更新してください。