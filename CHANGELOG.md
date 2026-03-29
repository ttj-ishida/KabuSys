# Changelog

すべての重要な変更点をこのファイルに記録します。このファイルは Keep a Changelog の形式に従い、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-29

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点・設計方針・注意点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。公開モジュール群として data, research, ai, strategy, execution, monitoring（__all__ に一部記載）を想定。

- 環境設定管理 (src/kabusys/config.py)
  - Settings クラスを追加し、環境変数を一元管理。
  - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。読み込み順は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト用）。
  - .env パーサー実装（export 形式・クォート・バックスラッシュエスケープ・インラインコメントの取り扱い対応）。
  - 環境変数の必須チェック用 _require を実装。JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などをプロパティで公開。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパス解決、KABUSYS_ENV / LOG_LEVEL のバリデーション、is_live/is_paper/is_dev の便宜プロパティを追加。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (news_nlp.py)
    - raw_news / news_symbols を用いたニュース集約 → OpenAI(gpt-4o-mini) による銘柄単位センチメント評価。
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST に対応、UTC に変換して DB と比較）。
    - バッチ処理（1 API コールにつき最大20銘柄）、1銘柄あたり最大記事数と最大文字数でトリム。
    - JSON Mode を使用した厳密な JSON 応答期待とレスポンス検証ロジック（余計な前後テキストを含む場合の復元処理を含む）。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）＋指数バックオフ。
    - レスポンス検証失敗や API エラー時は該当チャンクをスキップ（フェイルセーフ）、処理結果を ai_scores テーブルへ（部分成功を考慮して DELETE → INSERT の置換処理）。
    - 単体テスト容易性のため _call_openai_api の差し替えを想定。

  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して、日次の market_regime を算出／保存。
    - prices_daily からの ma200_ratio 計算、raw_news からマクロキーワードでタイトル抽出、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime テーブルへの冪等書込（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment = 0.0 で続行するフェイルセーフ。
    - OpenAI 呼び出しの失敗ハンドリング（RateLimit/接続/タイムアウト/5xx に対するリトライ）と JSON パースの堅牢化。
    - テスト容易性のため _call_openai_api はモジュール内で独立実装（news_nlp と共有しない設計）。

- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を用いた営業日判定ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に登録がない日については曜日ベース（土日除外）でフォールバック。DB 登録値が優先される一貫した振る舞いを提供。
    - 夜間バッチ更新処理 calendar_update_job 実装（J-Quants API との差分取得・バックフィル・健全性チェック・保存）。
    - 最大探索範囲やバックフィル日数、先読み日数などの定数化。

  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを定義し、ETL 実行結果（取得数／保存数／品質問題／エラー一覧）を構造化。
    - 差分取得・バックフィル・品質チェックの方針を反映した実装インターフェース（jquants_client と quality モジュールを利用する想定）。
    - data.etl から ETLResult を再エクスポート。

- 研究用モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から PER・ROE を計算（target_date 以前の最新財務データを参照）。
    - DuckDB 上の SQL を用いた効率的な実装（lookback バッファや行数チェックによる None 返却を含む）。

  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得（LEAD を利用）。
    - calc_ic: スピアマンのランク相関を実装（ties は平均ランク）。
    - rank: 値→ランク変換（同順位は平均ランク、丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージの __init__ で主要 API を公開。

### 変更 (Changed)
- 設計方針の明確化（全モジュール）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない実装方針を各所に適用（関数は target_date を明示的に受け取る）。
  - 外部ライブラリ（pandas 等）への依存を避け、標準ライブラリ＋duckdb で完結する実装を採用。
  - DB 書き込みは可能な限り冪等（DELETE→INSERT／ON CONFLICT など）にし、部分失敗時に既存データを不必要に消さない設計。

### 修正 (Fixed)
- DuckDB の executemany に空リストを渡せない挙動に対処
  - ai.news_nlp と pipeline の DB 書き込み処理で executemany に渡す前に空チェックを入れることで、DuckDB 互換性の問題を回避。

- API レスポンスパースの堅牢化
  - OpenAI の JSON mode を期待しつつも、前後に余計なテキストが混入するケースや整数で返される code を文字列へ正規化するなど、実運用で起きうるフォールトに対処。

### 注意 (Notes)
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未指定の場合は ValueError を送出する箇所が多数あり、呼び出し側での管理が必要。
- DuckDB 接続を直接受け取る設計のため、呼び出し側で適切に conn を開閉・トランザクション管理する必要がある（モジュール内でも BEGIN/COMMIT/ROLLBACK を適切に扱う場面あり）。
- ニュース集約やファクター計算は DB 内のテーブル構造（raw_news, news_symbols, prices_daily, raw_financials, market_calendar, ai_scores, market_regime 等）に依存するため、スキーマ整備が前提。
- 現時点で外部発注（ブローカー API）や実際のポジション管理ロジックは含まれておらず、研究・データ基盤・シグナル生成に重点を置いた実装。

---

今後の予定（例）
- strategy / execution / monitoring パッケージの実装強化（バックテスト・発注・運用監視）。
- テストカバレッジ拡大、CI ワークフローの整備、ドキュメント充実。

（初期リリースのため既知の制約や改善余地が存在します。バグ報告や改善提案は歓迎します。）