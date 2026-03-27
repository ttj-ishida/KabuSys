# Changelog

すべての変更は「Keep a Changelog」仕様に従い記載しています。セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームの基盤モジュール群を追加しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント処理など細かなパース仕様を実装。
  - 環境変数保護（protected keys）を利用した上書き制御。
  - Settings クラスを追加し、アプリで使用する設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダー取得・保持ロジック、営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル／健全性チェック付き）。
    - DB データがない場合の曜日ベースフォールバックを実装（堅牢性重視）。
    - 最大探索範囲で無限ループ回避（_MAX_SEARCH_DAYS）。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェックフレームワークの枠組みを実装。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）。
    - 各種定義（バックフィル、最小データ日付、カレンダー先読等）。

- AI ニュース処理（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（target_date の前日 15:00 JST ～ 当日 08:30 JST を UTC naive datetime に変換）。
    - score_news: OpenAI（gpt-4o-mini、JSON モード）を使ったバッチセンチメント解析を実装。特徴:
      - 1チャンク最大 20 銘柄、1銘柄あたり最大記事数/最大文字数でトリム。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ。
      - レスポンス検証（JSON 抽出、results リスト、code/score の検証、数値検証、スコア ±1.0 クリップ）。
      - スコア取得後は ai_scores テーブルに対象コードのみを DELETE→INSERT（部分失敗時に既存データ保護）。
      - テスト容易性のため API キー注入（api_key 引数）と _call_openai_api のパッチ可能化。
      - API 失敗時はフェイルセーフでスキップ・継続（例外を上げない仕様）。
  - レジーム判定（regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date より前のデータのみ使用、データ不足時は中立値 1.0 を使用）。
    - マクロ記事抽出は news_nlp.calc_news_window を利用し、キーワードフィルタでタイトルを収集。
    - OpenAI 呼び出しは同様に gpt-4o-mini（JSON モード）、リトライ、エラー時のフェイルセーフ macro_sentiment=0.0。
    - 最終結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - モジュール間でのプライベート関数共有を避ける設計（各モジュールで独自の _call_openai_api を持つ）。

- リサーチ / ファクター（src/kabusys/research/*）
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日 MA 乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播を制御し正確なカウントを行う。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を算出（EPS=0/欠損時は None）。
    - いずれも prices_daily / raw_financials のみ参照し外部 API 呼び出しは行わない設計。
  - feature_exploration.py
    - calc_forward_returns: リードを使い任意ホライズン（デフォルト [1,5,21]）の将来リターンを一回のクエリで取得。ホライズン検証（1〜252）を実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。同値（ties）は平均ランクで処理。
    - rank: ランク変換（同順位は平均ランク、丸めによる ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算するユーティリティ。
  - research パッケージの __init__.py で主要関数を公開。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス回避: 日付判定・ウィンドウ計算等で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計になっています（テスト容易性と再現性確保）。
- OpenAI 呼び出しは JSON モードを使用し、応答パースは厳格かつ寛容（前後余計なテキストが混入した場合の復元）に実装されています。LLM 失敗時は過度な例外伝播を避け、フェイルセーフ値（0.0 等）で継続します。
- DuckDB 互換性対策をいくつか導入（executemany の空リスト回避、日付値の型変換ユーティリティ等）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT DO UPDATE 等）してあり、部分失敗時に既存データが不必要に消えないよう配慮しています。
- テストしやすさに配慮: OpenAI クライアント注入、内部 _call_openai_api の差し替えが容易、環境変数自動読み込みオフのフラグあり。

---

今後の予定（議案）
- strategy / execution / monitoring の具体的実装（現時点ではパッケージ公開のみ）。
- ドキュメントの拡充（API 使用例、運用手順、DB スキーマ仕様）。
- CI テスト・ユニットテストの追加（特に LLM 呼び出し周りのモックテスト）。
- 追加の品質チェックルールやエラーレポート仕組みの強化。