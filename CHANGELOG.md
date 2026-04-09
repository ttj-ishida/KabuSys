# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-09
初期リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を実装しました。以下の主要な機能と設計方針を含みます。

### 追加 (Added)
- パッケージ基礎
  - パッケージ用エントリポイントを追加（src/kabusys/__init__.py）。バージョン情報 __version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルとOS環境変数から設定を読み込む自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env パース処理を強化：コメント・export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 環境変数保護（protected set）を導入し、override 処理時に既存OS環境変数の上書きを防止。
  - Settings クラスを実装し、各種設定値（J-Quants / kabuステーション / LINE / DB パス / Paper Trading モード / 監視設定 / システム環境等）をプロパティで提供。
  - 設定値のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を実装。必須変数未設定時には ValueError を送出。

- AI ニュース処理 (src/kabusys/ai/)
  - ニュース NLP スコアリングモジュールを実装（src/kabusys/ai/news_nlp.py）。
    - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄ごとのセンチメントスコアを生成。
    - 時間ウィンドウの計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄 / リクエスト）・記事数/文字数トリム（1銘柄あたり最大記事数/文字数）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他エラーはスキップしてフェイルセーフを維持。
    - レスポンスバリデーション: JSON 抽出、"results" 構造検証、未知コード無視、スコア数値検証、±1.0 でクリップ。
    - DuckDB への書き込みは冪等的に実行（対象コードのみ DELETE → INSERT）。DuckDB executemany の空リスト制約に配慮。
    - API キー注入可能（引数 api_key または OPENAI_API_KEY 環境変数）。未設定時は ValueError。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - 公開API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定モジュールを実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（"bull"/"neutral"/"bear"）を判定。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を取得。
    - API 再試行・エラー時は macro_sentiment=0.0 にフォールバックし継続。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックして例外を伝播。
    - API キー注入可能。公開API: score_regime(conn, target_date, api_key=None)

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research モジュールを実装（calc_momentum, calc_value, calc_volatility）。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - Value: raw_financials から最新財務データを取得して PER（EPS が 0/欠損の場合は None）と ROE を計算。
    - Volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を算出。必要行数未満は None。
    - DuckDB 上で SQL ウィンドウ関数を利用して効率的に実装。関数は prices_daily / raw_financials のみ参照し副作用なし。
  - feature_exploration モジュールを実装（calc_forward_returns, calc_ic, rank, factor_summary）。
    - 将来リターン（複数ホライズン）を一括クエリで取得。horizons の検証あり。
    - IC（Information Coefficient）をスピアマンのランク相関で計算。3件未満は None。
    - rank: 同順位は平均ランクを返す実装（丸めによる ties 対策を実施）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を標準ライブラリのみで算出。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management モジュールを実装。
    - market_calendar ベースで営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録がある場合は DB 値優先、未登録日は曜日ベースでフォールバック（週末判定）。探索は最大 _MAX_SEARCH_DAYS で打ち切り。
    - 夜間バッチ更新 job を実装（calendar_update_job）：J-Quants から差分取得して market_calendar を冪等に保存。バックフィル・健全性チェックあり。
    - jquants_client との統合（fetch_market_calendar / save_market_calendar を想定）。

  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを公開（ターゲット日・取得数・保存数・品質問題・エラーリスト等を含む）。
    - ETL の設計指針を反映：差分更新、バックフィル、品質チェック（quality モジュール）との連携、id_token 注入可能性など。
    - etl モジュールでは pipeline.ETLResult を再エクスポート。

### 変更 (Changed)
- 設計上の決定・方針をコードに明記
  - ルックアヘッドバイアス回避のため、各モジュール（ニュース/レジーム/リサーチ/ETL 等）は datetime.today() / date.today() を直接参照しない設計（全て target_date を受ける）。
  - DuckDB の互換性（executemany に空リスト渡せない問題等）を考慮した実装と注釈を追加。
  - OpenAI 呼び出し箇所はテストで差し替えやすいようプライベート関数を用意（モジュール間で共有しない方針）。

### 修正 (Fixed)
- ロギングとフェイルセーフの強化
  - LLM/API 呼び出し失敗時のログ出力とフォールバック（macro_sentiment=0.0、スコア取得失敗のスキップ等）を一貫して実装。
  - DB 書き込み処理での例外発生時に ROLLBACK を試行し失敗ログを出力するガードを追加。

### セキュリティ (Security)
- API キー管理
  - OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY から取得。未設定時は例外を発生させる（明示的なエラー）。
  - .env 自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。既存のOS環境変数は自動ロードで上書きされないよう保護。

---

注記:
- 本リリースはデータ処理・研究・AI スコアリング・カレンダー管理等のコア機能を備えた初期版です。発注／実行周り（strategy / execution / monitoring の具象実装）はパッケージ公開の想定 API として名前空間に残されていますが、本差分に含まれる具体実装は上記モジュール中心です。
- テスト容易性を考慮して外部API呼び出し点（OpenAI, J-Quants など）は差し替え可能な設計になっています。