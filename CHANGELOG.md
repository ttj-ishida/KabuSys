# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
- マイナー修正やドキュメント追加、テスト補強などは将来のリリースで記載します。

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ初期化とエクスポート
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。
  - `__all__` で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行い、配布後でも CWD に依存しない設計。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能（テスト用）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - OS 環境変数を保護するための protected set を扱う実装。
  - 高度な .env パーサーを実装（`export` プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなど）。
  - 必須取得用ユーティリティ `_require` と `Settings` クラスを追加。
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを提供。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（許容値チェック）。
    - `is_live` / `is_paper` / `is_dev` のユーティリティプロパティを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄毎にニュースを集約し OpenAI（gpt-4o-mini）でセンチメント評価。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄当たり記事数・文字数のトリム制御を実装。
    - JSON Mode を利用した厳格なレスポンス期待とパース・バリデーションロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - エラーやパース失敗時は例外を投げずフェイルセーフに 0 件スキップまたは該当銘柄を無視する挙動。
    - DuckDB の executemany の挙動（空リスト不可）に対するガードを実装し、部分失敗時に既存スコアを保護するために DELETE→INSERT の順で部分置換を行う。
    - 公開 API: `score_news(conn, target_date, api_key=None)`（書き込みした銘柄数を返す）。
    - ニュース収集ウィンドウ計算ユーティリティ `calc_news_window` を提供（JST 基準の時間窓を UTC naive datetime で返す）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジームを日次判定。
    - マクロニュース抽出用キーワード群と最大取得記事数を設定。
    - OpenAI 呼び出しは JSON モードで行い、再試行や 5xx の扱いを考慮。
    - API 失敗やパース失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - DB（DuckDB）への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: `score_regime(conn, target_date, api_key=None)`（成功時 1 を返す）。

- データモジュール（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェックを想定した ETL のインターフェースを実装。
    - ETL 実行結果を表す `ETLResult` データクラスを追加（品質問題、エラー集計、集計プロパティを含む）。
    - DuckDB 接続を前提とした最大日付取得やテーブル存在チェックなどのユーティリティを実装。
  - ETL の公開インターフェース `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - マーケットカレンダ管理（kabusys.data.calendar_management）
    - `market_calendar` を使った営業日判定ユーティリティ群を実装：
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動を採用。
    - 夜間バッチ `calendar_update_job` を実装（J-Quants API 経由で差分取得→冪等保存、バックフィル、健全性チェック）。
    - 検索範囲の最大日数やバックフィル幅、先読み日数等の定数を定義。

- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR / 相対 ATR）、Value（PER / ROE）を計算する関数を実装。
    - DuckDB を用いた SQL ベースの実装で、データ不足時は None を返す安全設計。
    - 公開 API: `calc_momentum`, `calc_volatility`, `calc_value`（それぞれ date, code をキーとする dict のリストを返す）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、入力検証あり）。
    - IC（Spearman ランク相関）計算 `calc_ic`（欠損除外、最小レコード数チェックあり）。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary`（count/mean/std/min/max/median を計算）。
  - `kabusys.research.__init__` にて主要関数を再エクスポート（研究用 API を集約）。

### Changed
- 設計方針・挙動に関する共通事項（プロジェクト全体で適用）
  - ルックアヘッドバイアス防止のため、全ての処理で datetime.today() / date.today() を直接参照しない設計を採用（関数は target_date を明示的に受け取る）。
  - OpenAI 呼び出しはすべて JSON 出力を期待し、レスポンスパースの堅牢化とフォールバック（JSON 抽出）を実装。
  - API 呼び出し失敗時はフェイルセーフ（ゼロやスキップ）で継続する方針を採用し、バッチ処理中の一部失敗が全体を止めない設計。
  - DuckDB の挙動差（executemany の空リスト不可など）を考慮した実装に変更。

### Fixed
- N/A（初回リリースのため、バグ修正履歴はなし）

### Deprecated
- N/A（初回リリースのため、非推奨はなし）

### Removed
- N/A（初回リリースのため、削除項目はなし）

### Security
- OpenAI API キーや各サービスのシークレットは Settings 経由で環境変数から取得し、.env の自動読み込みでは OS 環境変数を上書きしない保護機構を実装（安全性に配慮）。

---

注意・既知の制限:
- OpenAI や J-Quants など外部 API 呼び出しはネットワーク・料金・レート制限の影響を受けます。再試行やフォールバックは実装していますが、完全な可用性は保証しません。
- ai モジュールは LLM レスポンスに強く依存します。期待する JSON フォーマットでない場合は該当チャンクをスキップする動作となります。
- DuckDB のバージョン差異に起因する挙動（型バインド、executemany の制約等）は考慮していますが、環境差により追加調整が必要となる場合があります。
- 本リリースは主に内部ライブラリ・分析・ETL の実装に重点を置いており、実際の発注（execution）や運用（monitoring）連携は別モジュール（パッケージ構成上は存在）へ委任します。README / ドキュメントで利用方法を補う予定です。