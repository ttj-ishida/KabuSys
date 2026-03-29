# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース (0.1.0) に含まれる主要な追加事項と設計上の注意点を記載します。

## [Unreleased]

- 開発中の変更点や小さな改善はここに記載します。

## [0.1.0] - 2026-03-29

Added
- パッケージ初期公開
  - パッケージメタ情報を追加 (src/kabusys/__init__.py)。
  - サブパッケージを公開: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env/.env.local の自動読み込み実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - コメント扱いのルール（クォートなしの場合は '#' の直前がスペース/タブであるとコメント判定）を実装。
  - 環境変数の読み取りユーティリティ `_require` と Settings クラスを提供:
    - J-Quants / kabu / Slack / DB パス等のプロパティを提供。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証（許容値チェック）。
    - is_live / is_paper / is_dev の判定ヘルパー。

- AI モジュール (src/kabusys/ai)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成。
    - OpenAI (gpt-4o-mini) の JSON Mode を用いたバッチスコアリングを実装（最大バッチサイズ 20）。
    - 1銘柄あたりの記事数上限・文字上限によるトークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行ポリシー: 429・ネットワーク断・タイムアウト・5xx に対し指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション、数値変換、±1.0 でのクリップ。
    - DuckDB 互換性考慮: executemany に空リストを渡さないガード（DuckDB 0.10 対応）。
    - テストのために OpenAI 呼び出しを差し替え可能（内部 `_call_openai_api` をモック可能）。
    - タイムウィンドウ計算ユーティリティ `calc_news_window` を提供（JST 基準の前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組合せて日次レジームを判定。
    - マクロキーワードによる raw_news フィルタリングと LLM によるセンチメント評価（gpt-4o-mini、JSON 出力想定）。
    - API 再試行ロジック、API 失敗時のフォールバック（macro_sentiment=0.0）を実装しフェイルセーフに設計。
    - レジームスコアの合成、ラベル決定 (bull / neutral / bear)。
    - DuckDB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行うことで安全な更新を実現。
    - テストでの差し替えを容易にするために OpenAI 呼び出し関数を独立実装。

- Research（因子・特徴量分析） (src/kabusys/research)
  - ファクター計算群 (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を計算。
    - Volatility & Liquidity: 20 日 ATR（atr_20）/ 相対 ATR（atr_pct）/ 20日平均売買代金/出来高比率。
    - Value: raw_financials と prices_daily を用いた PER / ROE の算出（EPS=0/欠損時は None）。
    - DuckDB のウインドウ関数を活用した効率的な実装。
    - データ不足時の None 返却やログ出力による堅牢性。
  - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 (`calc_forward_returns`)：任意のホライズンに対するリターン算出（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算（Spearman の ρ 相当）`calc_ic`。
    - ランク変換ユーティリティ `rank`（同順位は平均ランク、丸め処理で ties の漏れを防止）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - 研究用ユーティリティの再エクスポートを提供（zscore_normalize 等）。

- Data プラットフォーム / ETL (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー (market_calendar) を用いた営業日判定ロジックの実装:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止と健全性チェック。
    - 夜間バッチ更新 job `calendar_update_job`：J-Quants から差分取得 → save_market_calendar（jquants_client）による冪等保存。バックフィル・健全性チェックを実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETL 処理のための設計とヘルパーを実装。
    - ETL 実行結果を表す dataclass `ETLResult` を提供（品質チェック結果やエラー集約、辞書化ユーティリティを含む）。
    - jquants_client と quality チェックの統合を想定した構造。

- 内部設計／運用面の配慮
  - ルックアヘッドバイアス対策: 各モジュールは datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - OpenAI 呼び出しはモジュールごとに独立実装し、テスト時に差し替え可能。
  - API 失敗時のフェイルセーフ戦略（中立スコア・スキップ・ログ出力）を幅広く採用。
  - DuckDB のバージョン差異に配慮した実装（executemany 空リスト回避など）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- 実行に必要な外部依存:
  - duckdb が主要な DB バックエンドとして使用される前提。
  - OpenAI SDK（OpenAI クライアント）を使用しているため、環境変数 `OPENAI_API_KEY` または各関数呼び出しで api_key を渡す必要があります。
- .env 読み込みはプロジェクトルートの検出に依存するため、パッケージ配布後や CWD が異なる環境下でも期待通り動作するよう設計されていますが、必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- DB 書き込みは冪等性を重視しているものの、呼び出し側でトランザクション整合性やエラーハンドリングを行うことを推奨します。
- API 呼び出し失敗時は一部データをスキップして処理を継続する挙動が多く見られます（フェイルセーフ）。運用時はログ監視や再実行フローを用意してください。

---

（項目追加・バグ修正・ドキュメント追記などの差分は今後のリリースにて本 CHANGELOG に追記していきます。）