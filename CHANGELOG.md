Keep a Changelog 準拠の CHANGELOG.md（日本語）を作成しました。リポジトリのコード内容から推測して記載しています。

# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

## [Unreleased]

- 今後のリリースで追加・変更予定の項目をここに記載します。

## [0.1.0] - 2026-04-02

Added
- パッケージ初期リリース: kabusys v0.1.0 を公開。
- 基本パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ の公開 API を設定。

- 設定 / 環境変数管理
  - src/kabusys/config.py
    - .env と .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
    - 読込順序: OS環境変数 > .env.local (override=True) > .env (override=False)。既存の OS 環境変数は保護（protected）される。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
    - .env パーサは以下をサポート:
      - コメント行、先頭の export キーワード、シングル/ダブルクォート、エスケープシーケンス、インラインコメントの扱い（クォート内は無視）。
    - Settings クラスを提供し、以下の設定プロパティを取得:
      - J-Quants / kabu API / Slack / DB パス（DuckDB / SQLite）/ 監視閾値（CPU/メモリ/ディスク）/ システム env と log_level の検証など。
    - Settings.env と Settings.log_level は許容値チェックを行い、不正な値の場合は ValueError を送出。

- AI モジュール
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でバッチ評価して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む機能を実装。
    - 処理の特徴:
      - JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を calc_news_window で提供。
      - 銘柄ごとに最新 N 記事を集約し、1銘柄あたりの文字数上限でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ _BATCH_SIZE（デフォルト 20）で API へチャンク送信。
      - 429 / ネットワーク / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンスは JSON モードで受け取り、厳密なバリデーションを実施。部分的に無効な応答は無視し、正常な銘柄のみを書き込む。
      - DuckDB の executemany の特性を考慮し、DELETE/INSERT を個別パラメータで実行して冪等性を確保。
      - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
      - テストしやすさを考慮し、内部の OpenAI 呼び出し関数は差し替え可能（unittest.mock.patch 推奨）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
    - 処理の特徴:
      - prices_daily から過去 _MA_WINDOW (=200) 日のデータを使って latest_close / MA200 の比率を計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得し、OpenAI（gpt-4o-mini）で macro_sentiment を算出（記事が無ければ LLM 呼び出しを行わず 0.0 を使用）。
      - API 呼び出しは再試行ロジックとエラー時のフェイルセーフ（macro_sentiment=0.0）を備える。
      - 最終スコアは閾値で "bull"/"bear"/"neutral" にラベリングし、DuckDB に対して冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込む。
      - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

- データ（Data Platform）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理を実装。market_calendar テーブルを参照して営業日判定や SQ 判定を提供。
    - 提供関数:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - 実装上の配慮:
      - market_calendar が未取得/まばらな場合は曜日ベースのフォールバック（土日は非営業日）。
      - next/prev/get_trading_days は DB 登録値を優先し未登録日は曜日ベースで補完、一貫した動作を保証。
      - 探索の最大範囲を _MAX_SEARCH_DAYS（デフォルト 60）で制限し無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル日数・健全性チェックを含む）。
    - jquants_client（外部モジュール）を用いて fetch/save を行う想定。

  - src/kabusys/data/pipeline.py / etl.py
    - ETL パイプラインの基本構成を定義。
    - ETLResult dataclass（src/kabusys/data/pipeline.py）を公開（src/kabusys/data/etl.py で再エクスポート）。
      - ETL 実行結果の構造（取得数/保存数/品質問題/エラー）を持ち、has_errors / has_quality_errors プロパティと to_dict() を提供。
    - 差分更新・バックフィル・品質チェックの方針とユーティリティ関数（テーブル存在チェック・最大日付取得など）を実装。

- Research（因子・特徴量）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算機能を提供:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。
      - calc_value: raw_financials から最新の EPS/ROE を参照して PER/ROE を計算（EPS が 0/欠損時は None）。
    - 実装特徴:
      - DuckDB を使った SQL ウィンドウ関数で効率的に計算。
      - ルックアヘッドバイアス回避のため date の扱いに注意（内部で date.today() を参照しない設計）。

  - src/kabusys/research/feature_exploration.py
    - 研究用途の統計・解析関数を提供:
      - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（デフォルト [1,5,21]）。
      - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効レコードが 3 件未満なら None。
      - rank: 値リストをランクに変換（同順位は平均ランク、丸め対策あり）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - 外部ライブラリに依存せず純粋な Python + DuckDB SQL で実装。

- テスト・運用面の配慮
  - OpenAI 呼び出し箇所は内部ラッパー関数化されており、unittest.mock.patch で差し替え可能。
  - LLM / API エラー時は例外を全面的に投げず、警告ログを出してフェイルセーフなデフォルト（例: 0.0）で継続する設計。部分成功時に既存データを保護するための部分置換ロジックを採用。
  - DuckDB の制約（executemany の空リスト不可など）への対応を実装。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Security
- 初版のため該当なし。

Notes / 実装上の重要事項（利用者向け）
- OpenAI API キーの取扱い:
  - news_nlp.score_news と regime_detector.score_regime は api_key 引数でキー注入可能。指定がなければ環境変数 OPENAI_API_KEY を参照。
- .env 自動読み込み:
  - パッケージインポート時に自動で .env / .env.local を読み込むため、テスト時など自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - 各モジュールは特定のテーブル（prices_daily / raw_news / news_symbols / market_regime / ai_scores / raw_financials / market_calendar 等）を参照します。実行前に期待されるスキーマが整っていることを確認してください。
- ルックアヘッドバイアス対策:
  - ほとんどの関数は datetime.today()/date.today() を直接参照しない実装方針です。target_date を明示することにより検証可能な時系列解析が可能です。

---

（注記）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートや変更履歴として正式に使用する場合は、実際のコミット履歴・差分に基づいて調整してください。