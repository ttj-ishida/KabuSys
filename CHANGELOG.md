# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

なお、以下の履歴は提供されたコードベースの内容から推測して作成した初期リリース向けの概要です。

## [0.1.0] - 2026-03-28
初回公開（ベースライン実装）。以下の主要機能と設計方針を実装しました。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: `kabusys`
  - エクスポートモジュール: `data`, `strategy`, `execution`, `monitoring`
  - パッケージバージョン: `0.1.0`

- 環境設定 / ロード機能 (`kabusys.config`)
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env 自動読み込み機能を実装（優先順: OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーで以下をサポート:
    - コメント・空行の無視
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント（クォート無しで直前が空白/タブの場合のみ）
  - `Settings` クラスを実装し、各種環境変数の取得とバリデーションを提供:
    - J-Quants, kabuステーション, Slack トークン/チャンネル、データベースパスなど
    - `env`（development/paper_trading/live）と `log_level` の検証
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`news_nlp.py`)
    - ニュース収集ウィンドウ計算 (`calc_news_window`)（JST ベースの UTC naive datetime）
    - raw_news / news_symbols から銘柄別に記事を集約するロジック
    - OpenAI（gpt-4o-mini、JSON Mode）へのバッチ送信（最大 20 銘柄 / チャンク）
    - リトライ／エクスポネンシャルバックオフ（429 / ネットワーク / タイムアウト / 5xx）
    - レスポンスバリデーション（JSON 抽出、結果形式、スコア数値化、既知コードのみ採用）
    - スコアの ±1.0 クリップ、ai_scores テーブルへの冪等的書込み（DELETE → INSERT）
    - テスト容易性を考慮した API 呼び出し差し替えポイント（_call_openai_api のモック化）
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して
      市場レジーム（`bull` / `neutral` / `bear`）を日次判定
    - ma200_ratio 計算時にルックアヘッドバイアスを防ぐ（target_date 未満のみ使用）
    - マクロ記事を抽出し LLM（gpt-4o-mini）で JSON レスポンスを期待してセンチメント取得
    - API 失敗時はフェイルセーフで `macro_sentiment = 0.0`
    - 冪等な market_regime テーブル書込み（BEGIN / DELETE / INSERT / COMMIT）
    - リトライとエラー種別ハンドリング（RateLimit / 接続エラー / timeout / 5xx の扱い）

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`factor_research.py`)
    - Momentum: 約1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB 上で SQL により効率的に実行。結果は (date, code) 単位の dict リストで返却
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（Spearman の ρ をランクで算出）
    - ランク変換ユーティリティ（同順位は平均ランク）
    - 統計サマリー（count/mean/std/min/max/median）
  - データ統計ユーティリティの再エクスポート（zscore_normalize）

- データプラットフォーム (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management.py`)
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - DB（market_calendar）優先、未登録日は曜日ベースのフォールバック
    - calendar_update_job: J-Quants クライアント経由で差分取得→冪等保存、バックフィル、健全性チェックを実装
  - ETL パイプライン (`pipeline.py`)
    - ETLResult dataclass（ターゲット日、取得/保存件数、品質問題、エラー等を集約）
    - テーブル存在チェック、最大日付取得などのユーティリティ
    - 差分更新／バックフィル方針、品質チェック連携のための構成を実装
  - ETL 結果型をトップレベルで公開（`data.etl` → `ETLResult`）

### 変更 (Changed)
- 設計上の重要方針を明記（コード内ドキュメント）:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装スタイル
  - DuckDB 特有の挙動（executemany に空リスト不可）への対応
  - 外部 API 呼び出しはフェイルセーフ（失敗しても例外を投げずにスキップまたはデフォルト値で継続）する方針
  - モジュール間でプライベート関数を共有しない（テスト容易性・モジュール結合低減）

### 修正 (Fixed)
- 初期実装につき、各種境界ケース（データ不足、NULL 値、API エラー等）に対する防御処理を追加:
  - MA200 計算でデータ不足時に中立値（1.0）を返却し WARNING ログを出力
  - market_calendar の NULL 値検出時に警告ログを出力して曜日フォールバックへ移行
  - OpenAI レスポンスの JSON パース失敗時に `{...}` 抽出ロジックで回復を試みる

### 既知の制限・注意点 (Known issues / Notes)
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（引数 or 環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出。
- raw_* / prices_daily / ai_scores / market_regime / market_calendar / raw_financials 等の DB テーブルが前提。テーブル未作成時の挙動は各関数のドキュメントを参照。
- news_nlp の出力パースは堅牢化しているが、LLM の想定外レスポンスには依然脆弱な面がある（パース失敗時は該当チャンクをスキップ）。
- value ファクターの一部（PBR、配当利回り）は未実装（将来的な追加予定）。
- 日時は UTC naive な datetime を内部的に使用する部分があり、タイムゾーン取り扱いは設計上明示的であるため利用時は注意が必要。
- jquants_client（外部モジュール）との依存があるが、実装は別モジュールとして分離されている（fetch/save 関数を呼び出す）。  

### セキュリティ (Security)
- .env 自動ロード時に OS 環境変数を保護するため、読み込み時に既存の OS 環境変数キーを保護集合（protected）として扱い、.env の上書きを制御。
- 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` によりテスト等で無効化可能。

### マイグレーション / 互換性 (Migration)
- 初期公開版のため既存互換性維持に関する注意点は無し。将来変更時は Settings の環境変数名や DB スキーマ変更に注意。

---

開発・テスト・運用に関する詳細（API 使用上の制約、DB スキーマ、J-Quants / kabu API の利用方法など）はプロジェクトのドキュメント（DataPlatform.md, StrategyModel.md 等）および各モジュールの docstring を参照してください。