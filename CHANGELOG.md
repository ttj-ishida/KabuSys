# CHANGELOG

全ての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従ってバージョン管理されています。

※本ファイルはコードベースからの推測に基づき作成しています。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-28
初期リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを導入。公開モジュールとして data, strategy, execution, monitoring を __all__ に設定。
  - バージョン: 0.1.0

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（読み込み優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応など）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティを公開。
  - 必須設定未定義時は明確な ValueError を送出するバリデーションを実装。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン骨格（kabusys.data.pipeline）
    - ETLResult dataclass により ETL 実行結果・品質問題・エラーを集計可能に。
    - 差分取得、バックフィル、品質チェックの方針を反映した設計。
  - ETL の公開インターフェースとして ETLResult を再エクスポート (kabusys.data.etl)。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無を考慮した営業日判定とフォールバック（DB 優先、未登録日は曜日ベースフォールバック）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job：J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）。
    - 最大探索・ループ保護のための制限（_MAX_SEARCH_DAYS 等）を実装。

- リサーチ（ファクター計算・特徴量解析）
  - kabusys.research パッケージに以下を実装・公開:
    - ファクター計算 (kabusys.research.factor_research)
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などを計算。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率などを計算。
      - calc_value: raw_financials からの EPS/ROE を用いた PER / ROE 計算（欠損時は None）。
      - DuckDB SQL を活用し、営業日ベースの窓処理を考慮。
    - 特徴量探索 (kabusys.research.feature_exploration)
      - calc_forward_returns: 指定 horizon に対する将来リターンを一括取得する汎用機能（horizons のバリデーションあり）。
      - calc_ic: スピアマンランク相関（Information Coefficient）を算出（データ不足時は None）。
      - rank: 同順位の平均ランク対応のランク変換ユーティリティ。
      - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - zscore_normalize は kabusys.data.stats から再エクスポート。

- AI / ニュース NLP（OpenAI 経由のセンチメント）
  - kabusys.ai.news_nlp
    - score_news: raw_news と news_symbols を元に銘柄毎のニューステキストを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価して ai_scores テーブルへ保存。
    - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を採用。calc_news_window を提供。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）、記事/文字数トリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理を実装。
    - API 応答パースの堅牢化（JSON 前後の余計なテキスト抽出など）。
    - テスト容易化のため _call_openai_api を patch 可能に設計。
  - kabusys.ai.regime_detector
    - score_regime: ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み70%）とニュースマクロセンチメント（重み30%）を合成して market_regime テーブルへ書き込み。
    - LLM 呼び出しは独立実装、失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 冪等 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI との対話は JSON モードを利用し、リトライ・バックオフ・エラーハンドリングを実装。

### 変更 (Changed)
- 初版のため該当なし（新規実装のみ）。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- 初版のため該当なし。

### 設計上の重要な注意点（ドキュメント的補足）
- ルックアヘッドバイアス防止:
  - 多くのスコアリング/判定処理で datetime.today()/date.today() を直接参照せず、target_date を明示的に与える設計。
  - DB クエリは target_date 未満 / 以外の排他条件を用いて過去データのみを参照。
- データベース操作:
  - DuckDB を前提とした SQL を多用。executemany の空リスト制約など DuckDB の挙動への配慮あり。
  - DB への書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 相当の扱い）。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）障害時は例外で即停止させず、可能な範囲でフォールバック（0.0 中立スコア等）して処理を継続する箇所がある。
- テスト親和性:
  - OpenAI 呼び出しなどは内部関数を patch できる設計でユニットテストを容易にしている。

### 既知の制約 / 未実装事項（現状の想定）
- 一部指標（PBR・配当利回りなど）は未実装（calc_value の Note に記載）。
- strategy / execution / monitoring モジュールの詳細実装は本スコープに含まれていない（パッケージ公開のみを示唆）。
- DuckDB のバージョン依存の挙動（リストバインド等）に注意。

---

（以上）