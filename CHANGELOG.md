# CHANGELOG

すべての注目すべき変更は Keep a Changelog に準拠して記載しています。  
このファイルはコードベースから推測した初期リリースの機能一覧・設計上の注意点を示します。

<!-- 参考: https://keepachangelog.com/ja/1.0.0/ -->

## [0.1.0] - 2026-04-02

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。
主要なサブパッケージ: kabusys.config, kabusys.ai, kabusys.research, kabusys.data, kabusys（パッケージ初期化）。

### 追加
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン定義（0.1.0）と公開サブパッケージを設定。

- 環境設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env/.env.local の優先順位と上書きルール（OS 環境変数保護）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート（テスト用）。
  - .env パーサーの強化:
    - コメント・空行・export プレフィックスに対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を正しくパース。
    - 行内コメント（クォートなしの場合は直前がスペース/タブであることを条件に扱う）に対応。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で提供:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視しきい値 / 環境（development/paper_trading/live）/ログレベル など。
    - 必須値は _require により ValueError を投げて明示。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へ送信しセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、チャンク内は記事数と文字数でトリム。
    - JSON mode を使った厳密な JSON 応答期待と、レスポンスのバリデーション処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - API 失敗やパース失敗はフェイルセーフでスキップ（例外を投げずログ出力）。
    - 成果は ai_scores テーブルへ（部分失敗に備えて対象コードで DELETE → INSERT を行い既存データを保護）。
    - calc_news_window ユーティリティを提供（JST を基準としたニュース集計ウィンドウ）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - prices_daily・raw_news を参照して ma200_ratio と titles を取得し、OpenAI で macro_sentiment を評価。
    - 失敗耐性: API 呼び出しが失敗した場合は macro_sentiment = 0.0 を採用して処理継続。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。
    - LLM 呼び出しは内部的に retry と JSON 解析を行い、5xx の再試行判定などを含む実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を算出。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを算出。NULL の取り扱いに注意。
    - calc_value: raw_financials から最新の財務（EPS, ROE）を取って PER/ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（<3）では None。
    - rank: 同順位は平均ランクを返す安定的なランク関数（round で丸めて ties 制御）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar テーブルに基づく営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB 未登録日は曜日ベースでフォールバック（週末を休日扱い）。
    - next/prev は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを回避。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック（未来日付の異常検知）を実装。
  - pipeline / etl:
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - ETL の差分取得・backfill・品質チェック（quality モジュールとの連携）を前提にした設計。
    - DuckDB 上でのテーブル存在チェックなどユーティリティを提供。

- 依存 / 設定に関する注意点（ドキュメントに明記）
  - OpenAI（OPENAI_API_KEY で指定）、J-Quants、kabuステーション API（KABU_API_PASSWORD 等）、Slack（SLACK_BOT_TOKEN/SLACK_CHANNEL_ID）などの環境変数が想定される。
  - データストアは DuckDB（デフォルトパス data/kabusys.duckdb）や SQLite（data/monitoring.db）を利用する設定を持つ。

### 変更（設計上の重要点）
- ルックアヘッドバイアス防止
  - 日付処理で datetime.today()/date.today() を直接参照しない設計（すべて target_date ベースで処理）。
  - prices_daily クエリに date < target_date（排他）等の条件を使うことで未来データの混入を防止。

- API 呼び出しの堅牢化
  - OpenAI 呼び出しは JSON mode を期待しながらもパース耐性を持たせ、部分的に余分なテキストが混入している場合は最外側の {} を抽出して復元する処理を導入。
  - 5xx / RateLimit / 接続タイムアウト等は指数バックオフでリトライ、その他はスキップしてログを残すフェイルセーフを採用。

- DB 書き込みの冪等性
  - market_regime / ai_scores 等へは既存レコードの削除 → 挿入（DELETE → INSERT）という手順で部分失敗時に既存データを保護する設計。

### 修正（不具合対応・安全措置）
- .env 応答のパースでエスケープ・クォート処理の不整合を防ぐためにパーサーを強化（バックスラッシュエスケープ対応）。
- DuckDB executemany に対する互換性配慮:
  - 空リスト渡しによる問題を回避するため、executemany 呼び出し前に空チェックを行う（ai_scores の書き込み等）。
- calendar_update_job における異常未来日付チェックを追加し、明らかなデータ異常時は更新をスキップ。

### 既知の制約 / 注意点
- OpenAI のレスポンスは外部依存のため、モデル変更や API 仕様変更に影響される可能性がある（status_code の有無など SDK 差分を考慮した実装あり）。
- raw_financials からの財務指標は報告日ベースで最新を拾うが、PBR や配当利回りは未実装。
- News NLP と Regime Detector は gpt-4o-mini を想定しているが、モデルの性能・料金に依存する点に注意。
- DuckDB のバージョン差異（リスト型バインドの挙動等）に対して互換性処理を入れているが、環境によっては追加の調整が必要。

---

（以降のリリースでは Unreleased セクションを使って変更履歴を追記してください）