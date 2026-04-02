# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。  
慣例: 重要な変更は Breaking Changes として明記します。

## [Unreleased]

- （現時点のソース全体は初期公開版に相当します。将来の変更はここに記載されます。）

## [0.1.0] - 2026-04-02

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下はこのリリースで追加された主な機能・設計方針・既知の注意点です。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ = 0.1.0、公開サブモジュール: data, strategy, execution, monitoring。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み: プロジェクトルート (.git または pyproject.toml を基準) を探索して `.env` / `.env.local` をロード。OS 環境変数を保護する仕組みを実装。
  - .env パーサー実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントルールに対応。
  - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - 必須値取得用の _require と、各種設定プロパティ（J-Quants トークン、kabu API、Slack、DB パス、監視閾値、環境/ログレベル判定等）を提供。
  - 設定値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事のセンチメントスコアリング機能を実装。
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信。
    - バッチサイズ、記事・文字数上限、リトライ（429 / ネットワーク / 5xx）を備えた堅牢な呼び出し。
    - レスポンス検証・パース保護（余分な前後テキストの復元、数値チェック、未知コードの無視）。
    - ai_scores テーブルへの冪等的な書き込み（対象コードのみ DELETE → INSERT）。
  - regime_detector: 市場レジーム判定機能を実装。
    - ETF(1321) の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull / neutral / bear）を算出。
    - prices_daily / raw_news を参照、OpenAI 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 でフォールバック。
    - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データ基盤 (kabusys.data)
  - calendar_management: JPX マーケットカレンダー管理と営業日ロジックを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が空のときは曜日ベース（週末休場）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル、健全性チェックを実装。
  - pipeline / etl: ETL の公開インターフェースと ETLResult を実装（差分取得・保存・品質チェックを想定）。
    - ETLResult: ETL 実行の集計/監査用データクラス（品質問題、エラー一覧、書き込み件数等を保持）。
    - エラーと品質問題の集約ロジック（致命的エラー検出フラグ、品質エラー判定）。

- 研究・因子解析 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS=0/欠損は None）。
    - DuckDB SQL による実装で、prices_daily / raw_financials のみ参照。返却は (date, code) キーの dict リスト。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク）相関を計算（有効レコード 3 未満で None）。
    - rank: 平均ランク（同順位は平均）を返すユーティリティ。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- その他ユーティリティ
  - 多数の設計上の安全策（冪等書き込み、ルックアヘッドバイアス防止のため date.today() を直接参照しない、DuckDB 互換の executemany 空チェックなど）を採用。

### 変更 (Changed)
- 初期実装につき履歴の変更項目はなし（新規追加）。

### 修正 (Fixed)
- 初期実装につき既知のバグ修正履歴はなし。

### 注意事項 / 既知の設計上の振る舞い
- OpenAI API の使用
  - gpt-4o-mini を JSON モード（response_format {"type": "json_object"}）で利用する前提。API キーは引数または環境変数 OPENAI_API_KEY で指定。
  - API エラー・パース失敗時は安全側としてスコア 0.0 を使用（プロセスを停止させない）。
- データベース
  - DuckDB を前提とした SQL を使用。DuckDB のバージョン差異に備えた実装（executemany の空リスト回避等）。
  - market_calendar / prices_daily / raw_news / ai_scores / market_regime / raw_financials 等のテーブル構造が存在することを前提とする。
- 環境設定
  - 実行には以下の環境変数等が必要:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（または関数引数）
  - 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml で特定して行う。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- ルックアヘッドバイアス対策
  - AI スコアリング・レジーム判定・ETL/研究モジュールのすべてで日付に関する「未来参照」を避ける設計（target_date 未満／以前のデータのみ参照）。
- フォールバック動作
  - マクロ記事が存在しない場合や API 失敗時は macro_sentiment=0.0 を採用。
  - market_calendar が未構築の場合は土日を休場扱いとするフォールバックを行う。
- ログ・バリデーション
  - 各所で警告ログを出して不整合を通知（例: データ不足、JSON パース失敗、ROLLBACK の失敗等）。

### 既知の制約 / 今後の検討点
- news_nlp の出力形式に強く依存（LLM が厳密な JSON を返すことを想定）。将来のモデル変更に備えたさらなる堅牢化が必要。
- DuckDB の型バインド/互換性問題（リストのバインド等）は運用実績に基づいて微調整が必要。
- J-Quants / kabu API のクライアント実装（kabusys.data.jquants_client など）は外部モジュールとして依存。実行環境での認証・レート制限ハンドリングが重要。

---

(注) 本 CHANGELOG は提示されたソースコードの内容と docstring / 実装から推測して作成しています。実装外の外部依存や運用に関する詳細はプロジェクトの別ドキュメント（README / DataPlatform.md / StrategyModel.md 等）を参照してください。