CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット:
- 変更は意味のある粒度でまとめています。
- 初回リリースは 0.1.0 として記載しています。

Unreleased
----------

（現在のところ未リリースの変更はありません）

0.1.0 - 2026-03-28
-----------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"
    - パブリックサブパッケージとして data / research / ai 等を想定（__all__ に "data", "strategy", "execution", "monitoring" を公開）

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
    - プロジェクトルート判定: .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - 高度な .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）
  - Settings クラスを提供し、各種必須設定をプロパティで取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック（未設定で ValueError 発生）
    - KABU_API_BASE_URL のデフォルト、DB ファイルパス（DUCKDB_PATH／SQLITE_PATH）などの既定値
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev の補助プロパティ

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄毎にテキストを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を対象、UTC に変換して DB クエリ）
    - バッチ化（最大 _BATCH_SIZE=20 銘柄）、記事数／文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score 検証、数値性チェック）
    - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルへトランザクション（DELETE → INSERT）で置換
    - テスト容易性: OpenAI 呼び出しは _call_openai_api を通すことで patch 可能
    - フェイルセーフ: API 呼び出し失敗時は該当チャンクをスキップし続行（例外を上位に投げない設計）

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定
    - prices_daily からの ma200_ratio 算出（ルックアヘッド防止のため target_date 未満データのみ使用）
    - raw_news からマクロキーワードでタイトルを抽出して LLM に送信、JSON で macro_sentiment を取得
    - API 障害時のフェイルセーフ: macro_sentiment=0.0（警告ログ）で継続
    - 生成スコアはクリップ処理後に閾値判定（_BULL_THRESHOLD/_BEAR_THRESHOLD）でラベル化
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）、失敗時は ROLLBACK を試行して例外伝播
    - OpenAI 呼び出し関数は news_nlp とは別実装としモジュール結合を低減

- Research / ファクター分析（src/kabusys/research）
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、avg_turnover、volume_ratio を計算
    - calc_value: raw_financials と prices_daily から PER / ROE を計算（EPS0/欠損時は None）
    - データ不足時の扱い（足りないウィンドウでは None を返すなど）
    - DuckDB を用いた SQL + Python の実装。外部 API にはアクセスしない設計
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度に取得。horizons のバリデーションあり
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。3 レコード未満は None を返す
    - rank: 同順位は平均ランクにする実装（丸めで tie 検出の堅牢化）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ実装
  - research パッケージ __init__.py で主要関数を再エクスポート

- Data プラットフォーム機能（src/kabusys/data）
  - calendar_management.py
    - market_calendar テーブルを利用した営業日判定ユーティリティを提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB の登録値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫した挙動
    - calendar_update_job: J-Quants API から差分取得 → 保存（fetch/save を jquants_client 経由）・バックフィル・健全性チェックを実装
    - 最大探索日数・バックフィル日数・サニティチェック等の保護機構を実装
  - pipeline.py / etl.py
    - ETLResult データクラス（ETL 結果集約、品質チェック結果やエラー列挙を含む）
    - 差分更新／バックフィルロジック、品質チェック（quality モジュール連携）を想定した ETL パイプラインユーティリティ
    - DuckDB のテーブル存在確認／最大日付取得ユーティリティを追加
    - etl モジュールは pipeline.ETLResult を再エクスポート

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのため修正履歴なし）

Security
- API キーやトークン（OpenAI, J-Quants, Kabu API, Slack 等）は環境変数として必須チェックを実装。未設定の場合は ValueError を発生させることで明示的に通知

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: AI モジュールや各種スコア算出処理は datetime.today() / date.today() を直接参照せず、必ず caller が渡す target_date を基準に処理する設計
- フェイルセーフ: OpenAI API 呼び出しや外部 API の障害時に処理全体を停止させない（できる限りロギングしてスキップまたはデフォルト値を使用）
- DuckDB を主要な分析 DB として使用。トランザクション（BEGIN/COMMIT/ROLLBACK）を明示して冪等性を確保
- テスト容易性: OpenAI 呼び出し箇所は内部関数を経由しており、unittest.mock.patch による差し替えが可能
- トランザクションの鍵となる実装（DELETE → INSERT）により部分失敗時の既存データ保護を意図

今後の予定（未実装/想定）
- strategy / execution / monitoring パッケージの実装（__all__ に含まれているため今後の追加を想定）
- 追加の品質チェックルールや監視アラート連携（Slack 通知等）
- パフォーマンス改善（大規模データセット向けの最適化）

--- 

この CHANGELOG はソースコードから推測して生成しています。実際のリリースノートとして使用する際は、実際のコミット・リリース内容に応じて適宜修正してください。