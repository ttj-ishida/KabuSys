Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

（なし）

0.1.0 - 2026-03-29
-----------------

Added
- 初期リリース。日本株自動売買/データ基盤向けのコアライブラリを追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
  - メインサブパッケージを __all__ で公開: data, strategy, execution, monitoring
- 環境設定/ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 環境変数上書き動作（.env と .env.local の優先度）、OS 環境変数保護（protected set）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定をプロパティ経由で取得。
  - KABUSYS_ENV / LOG_LEVEL の値検証、is_live / is_paper / is_dev のユーティリティ。
- AI 関連（src/kabusys/ai）
  - news_nlp.score_news: ニュース記事を OpenAI（gpt-4o-mini）でバッチ評価し、銘柄ごとのセンチメントを ai_scores テーブルへ保存するワークフローを実装。
    - JST ウィンドウ（前日15:00～当日08:30）を UTC に変換して対象記事を抽出。
    - 銘柄ごとに最大記事数・最大文字数でトリム、最大20銘柄/チャンクで API 呼出し。
    - JSON Mode レスポンスの検証・クリップ（±1.0）、部分失敗時に既存データを保護する差替えロジック（DELETE → INSERT）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数的バックオフリトライを実装。
    - テスト容易性のため API 呼び出し部は差し替え可能（unittest.mock.patch を想定）。
  - regime_detector.score_regime: ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（70%）とマクロ新聞の LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存する処理を実装。
    - ma200_ratio 計算は target_date 未満のデータのみを利用し、ルックアヘッドバイアスを防止。
    - マクロ記事はキーワードフィルタで抽出し、記事がある場合にのみ LLM 評価を行う。
    - API 失敗時は macro_sentiment=0.0 としてフォールバックし、処理継続（フェイルセーフ）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - 両モジュールとも OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY からも参照。
- データプラットフォーム（src/kabusys/data）
  - calendar_management:
    - JPX カレンダー（market_calendar）の管理・夜間バッチ更新（calendar_update_job）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日ユーティリティを提供。
    - DB 登録値を優先しつつ、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジックを実装。
    - カレンダー取得ではバックフィル・健全性チェック・lookahead を考慮。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール連携）を想定した ETL の基盤ユーティリティを実装。バックフィルや最小データ日付などの定数を用意。
    - ETLResult は品質問題やエラー情報を含めて辞書化可能（監査ログ用途）。
- Research（src/kabusys/research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（prices_daily のウィンドウスキャン、データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御を含む）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 欠損時は None）。
    - すべて DuckDB SQL による実装で外部 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None。
    - rank: 同順位は平均ランクとして扱うランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数。
  - research.__init__ で主要関数を再エクスポート。
- 共通実装の設計方針（横断的）
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を業務ロジックで直接参照しない設計（target_date を引数で受ける）。
  - DuckDB を一次データ層に利用し、SQL と Python の組合せで集計・ウィンドウ処理を実装。
  - DB 書き込みは可能な限り冪等性を担保（DELETE→INSERT、ON CONFLICT など）。
  - OpenAI 呼び出しはエラー耐性（リトライ、バックオフ、パース失敗時フォールバック）を重視。
  - テストしやすさを考慮し、API 呼出し部やキー注入箇所に差し替えフックを用意。

Changed
- 新規リリースのため過去バージョンからの変更は無し。

Fixed
- 初版リリースのため過去バージョンからの修正は無し。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の上書き時に OS 環境変数を保護する機構を導入（.env のロードで protected set を使用）。
- Settings により必須キー未設定時は ValueError を発生させて早期検出。
- LOG_LEVEL / KABUSYS_ENV の妥当性チェックを実装し、不正な値は拒否。

Notes / 実装上の注意
- OpenAI 連携部は gpt-4o-mini と JSON Mode を前提とした実装で、SDK の将来の変更（status_code の位置など）を考慮した防御的記述が含まれます。
- DuckDB の executemany に空リストを渡せない制約を考慮して、挿入前チェックを行っています（部分書込みで既存データ保護）。
- news_nlp/regime_detector など複数箇所で API キーを引数で注入可能にしており、テスト環境でのモック容易性を確保しています。
- マクロキーワードや各種閾値・バッファ日数はソース内定数として定義しており、将来的に設定化が容易な構造になっています。

Contributing
- バグ報告・機能提案は issue を作成してください。  
- コードスタイル・テストの追加を歓迎します（API 呼出し部分はモックしやすい構造を保つこと）。

License
- （リポジトリ側のライセンスに従ってください。ソース中に明示がない場合はリポジトリルートを参照してください。）