CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
安定版はセマンティック バージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
-------------------

初回リリース。

Added
- パッケージ基盤
  - kabusys パッケージ初版を公開。パッケージバージョンは 0.1.0。
  - kazubys.__all__ に data, strategy, execution, monitoring を公開予定の名前空間として定義。

- 環境・設定管理 (kabusys.config)
  - .env / .env.local を自動ロードする軽量パーサ実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。
  - .env のパース機能:
    - export プレフィックス対応、シングル/ダブルクォートの取り扱い（バックスラッシュエスケープ考慮）、インラインコメント規則（クォート外の '#' の扱い）。
    - ファイル読み込み失敗時の警告、override/protected キーの概念（OS 環境変数保護）。
  - Settings クラスで主要設定項目をプロパティ化:
    - J-Quants / kabuステーション / LINE API / DB パス / 監視設定 / システム設定等を取得。
    - env（development/paper_trading/live）と log_level のバリデーションを実装。
    - Path 型でのパス処理（expanduser）や閾値の型変換をサポート。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）:
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装。品質問題・エラー収集と to_dict 変換をサポート。
    - デフォルトのバックフィル、カレンダー先読み、最小データ日などの定数を定義。
  - calendar_management:
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値を優先し、登録がない日は曜日（平日）フォールバックする一貫した設計。
    - 夜間バッチ job (calendar_update_job) により J-Quants から差分取得 → 冪等保存（ON CONFLICT 相当）を実行。バックフィルや健全性チェックを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ／流動性（20日 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）計算機能を実装。
    - DuckDB での Window 関数を活用した SQL ベースの実装。データ不足時の None 処理やログ出力あり。
  - feature_exploration:
    - 将来リターン計算(calc_forward_returns)（horizons バリデーション付、単一クエリ実行で効率化）。
    - IC（Information Coefficient）計算 (calc_ic) — スピアマン順位相関（ties の平均ランク処理を含む）。
    - rank ユーティリティと factor_summary（count/mean/std/min/max/median）を実装。
  - research パッケージから主要関数をエクスポート。

- AI / ニュース NLP (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとの記事テキストを作成し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント ai_score を ai_scores テーブルへ保存する処理を実装。
    - ニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime 変換済み）。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたり記事数・文字数のトリム制御、JSON Mode 応答のバリデーションと復元処理（余分な前後テキストが混入する場合の {} 抽出）を実装。
    - 再試行ポリシー（429、ネットワーク、タイムアウト、5xx に対する指数バックオフ）および失敗時のフェイルセーフ（失敗銘柄をスキップ、他銘柄の既存データは保護するため部分置換ロジック）。
    - DuckDB の executemany の制約（空リスト不可）を考慮した実装。
  - regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM, 重み 30%）を合成して market_regime テーブルへ日次で書き込む機能を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、レスポンスの JSON パース、リトライ（429/ネットワーク/5xx 等）を備える。API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - レジーム判定（閾値に基づく bull / neutral / bear）と冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - AI モジュールはテスト容易性のため OpenAI 呼び出し部分を差し替え可能なよう設計（内部 _call_openai_api を patch 可能）。

Security / Reliability / Design decisions
- ルックアヘッドバイアス対策:
  - datetime.today() / date.today() を内部の判定に直接用いない設計（外部から target_date を注入）。
  - prices_daily クエリは target_date 未満／以降の排他条件を意識。
- エラー耐性:
  - OpenAI API 呼び出しは指定例外でリトライ、その他はフェイルセーフでスキップして処理継続。
  - DB 書き込みはトランザクションで冪等性（DELETE→INSERT）の実現。
  - ログ出力による問題可視化（warning/info/exception）。
- DuckDB 互換性:
  - executemany の空リスト回避など DuckDB 実装差分を考慮。
- テスト性:
  - OpenAI 呼び出し等を unittest.mock.patch で差替え可能にして単体テストを容易化。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Notes
- OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を送出する（明示的なエラー）。
- 今後のバージョンで strategy / execution / monitoring の具現化や public API の安定化を予定。

---

（この CHANGELOG はソースコードからの情報に基づいて生成されています。実際のリリースノートには追加の運用手順やマイグレーション情報を含めてください。）