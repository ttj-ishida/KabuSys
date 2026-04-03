# CHANGELOG

すべての注記は Keep a Changelog の形式に従います。  
リリース日はコードベースから推測した日付を記載しています。

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートの自動検出ロジック: .git または pyproject.toml を起点に探索し、CWD に依存しない探索を実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パース機能: コメント行／export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装。
    - override / protected オプションによる上書き制御（OS 環境変数の保護）。
  - Settings クラスを提供し、以下の主要設定プロパティを環境変数から取得:
    - J-Quants / kabuステーション / LINE Messaging / データベース（DuckDB / SQLite）/ 監視関連ファイルパス / CPU/Memory/Disk 閾値 / ログレベル / 実行環境種別（development/paper_trading/live）等。
    - 必須環境変数未設定時に ValueError を送出する _require() を導入。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性メソッド（is_live/is_paper/is_dev）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols から指定ウィンドウ（前日15:00 JST～当日08:30 JST）に対応する記事を抽出する calc_news_window と _fetch_articles を実装。
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング機能 score_news を実装。
    - バッチ処理（1 API コールにつき最大 20 銘柄）、1 銘柄あたりの記事数上限・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を導入してトークン肥大化を防止。
    - API 呼び出しに対する堅牢なリトライ戦略（429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフ）、およびレスポンス検証処理（JSON モードの余計な前後テキスト対応、results キー/型/スコアの数値チェック）。
    - スコアは ±1.0 にクリップ。結果は ai_scores テーブルへ idempotent に DELETE → INSERT で書き込む。部分失敗時に既存スコアを保護する設計。
    - API キー注入対応（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA 算出は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。データ不足時は中立（ma200_ratio=1.0）を採用。
    - マクロニュースは news_nlp.calc_news_window によるウィンドウで抽出し、OpenAI を呼んで macro_sentiment を算出（記事なしは LLM を呼ばず 0.0 にフォールバック）。
    - LLM 呼び出しは独立実装で、リトライ戦略・5xx 判定・例外ハンドリング・JSON パース失敗時のフォールバック（macro_sentiment=0.0）を備える。
    - 合成後のスコアを market_regime テーブルに冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。しきい値や重み等は定数化（_MA_WEIGHT/_MACRO_WEIGHT/_BULL_THRESHOLD/_BEAR_THRESHOLD）。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に情報がある場合はそれを優先し、未登録日は曜日ベース（平日）でフォールバックする一貫した振る舞い。
    - next/prev_trading_day は最大探索日数（_MAX_SEARCH_DAYS=60）で無限ループを回避。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル / 健全性チェックを実施）。J-Quants クライアントは jquants_client を利用。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを導入し、ETL 実行結果（取得数／保存数／品質問題／エラー等）を構造化して返却可能にした。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。ETLResult.to_dict() により品質問題を辞書化して出力可能。
    - ETL のデフォルト設定（最小データ日、カレンダー先読み、デフォルトバックフィル日等）を定義。

- リサーチ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum, calc_volatility, calc_value を実装。
      - Momentum: 約1/3/6ヶ月リターン、200日移動平均乖離（データ不足時は None を返す）。
      - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
      - Value: raw_financials から最新財務を取得して PER・ROE を算出（EPS が 0/欠損のとき PER は None）。
    - すべて DuckDB SQL を用いた実装で、外部 API へのアクセスを行わない設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns（翌日/翌週/翌月等の将来リターン計算）、calc_ic（スピアマン ρ による IC 計算）、rank（平均ランク処理）、factor_summary（count/mean/std/min/max/median 計算）を実装。
    - pandas 等の外部依存を持たない純標準ライブラリ実装。

- 再エクスポート / API 整理
  - ai モジュールで score_news / score_regime を公開（news_nlp の score_news を ai パッケージで再エクスポート）。
  - data.etl で ETLResult を上位モジュールに再エクスポート。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### セキュリティ (Security)
- OpenAI の API キー取り扱い:
  - api_key を関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は明示的にエラーを返すことで誤動作を防止。

### 注意事項 / 設計上のポイント
- ルックアヘッドバイアス対策:
  - AI / ファクター / ETL の各処理は datetime.today() / date.today() を直接参照せず、呼び出し元から target_date を受け取る設計になっています。
- フェイルセーフ設計:
  - 外部 API（OpenAI, J-Quants）呼び出し失敗時は処理を継続する設計（LLM 関連はスコア 0.0 へフォールバック、news スコアは該当コードをスキップ）で、システム全体の停止を避けます。
- DuckDB 互換性:
  - executemany に空リストを渡さないなど、DuckDB のバージョン特性を考慮した実装を行っています。
- 主要外部依存:
  - duckdb, openai（OpenAI SDK）。これらは本リリースでの主要外部依存です。

---

今後のリリースでは以下のような改善候補が想定されます:
- モデル/プロンプトの調整とテストカバレッジ拡充
- news_nlp/regime_detector の並列化・性能改善
- ETL の詳細な品質チェックルール拡張と自動修正オプション
- CLI / 管理 UI の整備

---