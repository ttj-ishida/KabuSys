# CHANGELOG

この変更履歴は Keep a Changelog の形式に準拠しています。  
初期リリースの内容は、リポジトリ内のソースコードから推測してまとめています（実装上の設計意図・挙動も併記）。

全般的な注意:
- 本プロジェクトは日本株自動売買/データ基盤を想定したライブラリ群で、DuckDB を内部データストアとして利用します。
- AI 関連は OpenAI (gpt-4o-mini) を JSON モードで利用する設計になっており、API 呼び出し失敗に対してフェイルセーフ（デフォルトスコアやスキップ）する仕組みが組み込まれています。
- ルックアヘッドバイアス防止のため、datetime.today() / date.today() を直接参照しない方針で実装されています（ターゲット日を引数で与える形）。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期公開
  - パッケージ名: kabusys、バージョン `0.1.0`。
  - パッケージの公開 API としてモジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能を追加（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パース実装:
    - コメント行、空行の無視。
    - `export KEY=...` 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値では `#` が直前にスペース/タブであればコメントとして扱う（インラインコメント対応）。
  - 環境変数取得ユーティリティ `_require` と Settings クラスを追加:
    - J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を実装。
    - Path を返す DB パスプロパティ（DuckDB / SQLite）。

- AI モジュール (`kabusys.ai`)
  - ニュースセンチメント分析 (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30 JST）を UTC に変換してクエリ。
    - 複数銘柄を最大 20 コードずつバッチ送信（_BATCH_SIZE=20）。
    - 各銘柄は最大記事数と最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しは JSON モードを期待し、レスポンスを厳密にバリデーション。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。非再試行エラーはスキップ。
    - スコアは ±1.0 にクリップ。部分成功時は取得した銘柄コードのみ ai_scores テーブルを置換（DELETE → INSERT）して既存データ保護。
    - テスト容易性を考慮し、API 呼び出し関数を差し替え可能（patch でモック化）。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily から MA200 比を計算する `_calc_ma200_ratio`（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - マクロ記事はキーワード（日本・米国・グローバルの主要ワード）でフィルタし、最新最大件数を抽出。
    - OpenAI 呼び出しは JSON モードで実行。API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、エラー時は ROLLBACK を試行し上位へ例外を伝播。

- リサーチ / ファクター計算 (`kabusys.research`)
  - factor_research:
    - calc_momentum: 約1/3/6ヶ月リターン、200日MA乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。NULL 伝搬とカウントを注意して処理。
    - calc_value: raw_financials を使い PER（EPS が 0/欠損なら None）と ROE を計算（target_date 以前の最新財務データを使用）。
    - 各関数は DuckDB の SQL を活用して高速に集計、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - calc_forward_returns: 指定日から将来ホライズンのリターン（デフォルト [1,5,21]）を計算。horizons の入力検証あり。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクにする実装（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- データ基盤 (`kabusys.data`)
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジック。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得時は曜日ベース（平日を営業日）でフォールバック。DB 登録がある日は DB 値を優先。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック付き）。
    - 最大探索日数や先読み・バックフィル日数等の定数を定義し無限ループを回避。
  - pipeline:
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）。
    - ETL 処理設計: 差分更新、idempotent 保存（jquants_client の save_* を利用）、品質チェックの収集方針を採用。
    - _get_max_date 等のユーティリティ実装。

- その他
  - 単純な __init__ エントリポイントやパッケージエクスポートを整備。
  - 外部 API クライアント (OpenAI, jquants_client) の注入やモック化を想定した設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）
  - ただし各モジュールにおいて、API失敗時のフォールバック動作や ROLLBACK の二重失敗ログ出力など堅牢性向上の実装が含まれる。

### Security
- API キー取り扱い:
  - OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY で供給する設計。未設定時は ValueError を発生させ処理を中断。
  - .env 自動読み込み時に既存 OS 環境変数を保護するため protected set を導入。

### Notes / Design decisions（設計上の重要事項）
- ルックアヘッドバイアス回避: 日次スコア算出系は内部で現在時刻を参照せず、必ず target_date を明示的に受け取る設計。
- DuckDB の互換性対策: executemany に対する空リスト回避やリストバインドの安定性を考慮した実装。
- 部分成功耐性: AI スコア取得や ETL の各処理は部分失敗を許容し、成功した部分のみ DB に書き込むことで既存データの不意な消失を防ぐ。
- テストしやすさ: `_call_openai_api` などの内部関数はテスト時にパッチで置き換え可能に実装。

---

今後の更新案（例）
- エラー・メトリクス収集の一層の強化（監視 / Retry ポリシーの細分化）
- News/NLP の多言語対応やモデル切替の柔軟化
- ETL の差分算出ロジック（営業日単位→レンジ単位）の拡張
- ドキュメント（API 仕様・デプロイ手順）の追加

（以上）