# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠して変更を記録します。  
日付はコードベースの内容から推測して記載しています。

全般的な方針:
- API 呼び出し失敗時はフェイルセーフ（例: LLM 呼び出し失敗時にスコアを 0 にフォールバック）として継続する設計が各所で採用されています。
- ルックアヘッドバイアスを避けるため、内部実装で datetime.today() / date.today() を直接参照しない設計になっています（関数呼び出し時に target_date を渡す方式）。
- DuckDB の互換性と挙動（executemany の空リスト制約等）を考慮した実装になっています。

なお、この CHANGELOG はソースコードから推測して作成したものであり、実際のリリースノートとは異なる可能性があります。

## [Unreleased]
- ドキュメントや例外メッセージの改善、内部ロギング追加（コードから推測）。
- テスト用フックの明示（例: OpenAI 呼び出しをパッチ差し替え可能な実装）。
- マジックナンバーや定数の整理（モデル名やバッチサイズ、ウィンドウ等が定数化済み）。

## [0.1.0] - 2026-03-31
初回リリース（推測）。以下の主要機能を実装。

Added
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール群: data, strategy, execution, monitoring（__all__ 指定）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメントの扱い（クォート無しの '#' は直前が空白/タブの場合のみコメントとして扱う）。
  - 必須環境変数取得用ヘルパー _require。
  - 設定オブジェクト Settings を提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI/NLP モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.score_news）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - バッチサイズ、トークン肥大化対策（記事数・文字数の制限）、JSON Mode を利用した堅牢な応答パースを実装。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスのバリデーション（results 配列、code/score の検証、スコアの有限性チェック）。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。部分失敗時に既存スコアを保護する設計。
    - テスト容易性向上のため _call_openai_api を patch で差し替え可能。
  - マクロレジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM モデル: gpt-4o-mini を使用。
    - LLM 呼び出しに対するリトライ/バックオフ実装、API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - DuckDB に対する冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアスを防ぐため、prices_daily クエリは target_date 未満のみ使用。

- データ処理 / ETL（src/kabusys/data）
  - ETL パイプラインのインターフェース（pipeline.ETLResult を公開）。
  - pipeline.ETLResult: ETL 実行結果の dataclass（取得件数・保存件数・品質問題・エラーの集約、シリアライズ用 to_dict）。
  - ETL 実装方針:
    - 差分更新、バックフィル（デフォルト 3 日）、品質チェックの設計が反映。
    - DuckDB との互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを提供。

- データカレンダー管理（src/kabusys/data/calendar_management.py）
  - JPX カレンダー管理機能（market_calendar テーブルの更新・夜間バッチ）。
  - 営業日判定ユーティリティ:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar のデータがない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて無限ループ防止。
  - calendar_update_job: J-Quants API から差分取得し冪等に保存するジョブを実装。バックフィル日数、先読み日数、健全性チェックを備える。
  - DuckDB 値の date 変換ユーティリティとテーブル存在チェックを実装。

- 研究（Research）モジュール（src/kabusys/research）
  - factor_research（calc_momentum, calc_volatility, calc_value）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER / ROE）を DuckDB の prices_daily / raw_financials から計算。
    - 欠損データの扱い（行数不足時は None を返す）やスキャン窓の設計（バッファ付き）を実装。
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターン計算（任意ホライズン、入力検証あり）。
    - IC（Spearman の ρ）計算の実装（ランク付けは同順位を平均ランクで処理）。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - data.stats から zscore_normalize を再エクスポートする仕組みを用意。

Changed
- 設計上の注意点をコード内で明文化（例: DuckDB の executemany 空リスト制約の回避、LLM レスポンスの堅牢なパース、ルックアヘッド防止設計など）。
- ロギングを多所に追加し、異常系での情報を詳細に出力するようにしている（例: API 失敗、ROLLBACK 失敗、JSON パース失敗、データ不足の警告など）。

Fixed
- （コードから推測される修正）.env パースや引用符・エスケープ、コメント扱いに関する頑健化。

Security
- OpenAI API キーや各種トークンは環境変数経由で読み込む設計。必須トークン未設定時は明確な ValueError を送出。

Notes / Implementation details（重要な設計判断）
- LLM 呼び出しは JSON mode を利用し、さらに前後に余計なテキストが混入するケースへの回復ロジック（最外の {} を抽出してパース）を備えることで実運用での堅牢性を高めている。
- AI 系の API 呼び出しはテスト時に差し替え可能な内部関数を用意しており、ユニットテスト容易性を考慮している。
- DuckDB の仕様やバージョン差異を念頭に置いた実装（例: executemany の空リスト回避、リストバインドの不安定性への対処）。
- どの関数も内部で現在日時を暗黙に参照しない（target_date を明示的に受け取る）ことで、再現性とバックテストの信頼性を担保している。

---

もし実際のリリースや差分（以前のバージョンからの変更点）に関する情報があれば、それに合わせて CHANGELOG を更新できます。必要であれば英語版やリリースノート生成（Git コミットや PR からの自動生成）用のテンプレートも作成します。