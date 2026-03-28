# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

### Added
- なし

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム KabuSys のコア機能を実装しました。以下の主要機能・モジュールを含みます。

### Added
- パッケージ基礎
  - パッケージ名 `kabusys`、バージョン `0.1.0` を設定。
  - パッケージ公開 API としてモジュール群をエクスポート（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の取り扱いを実装。プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行い、カレントワーキングディレクトリに依存しない実装。
  - .env のパースは以下に対応:
    - 空行・コメント行（先頭 `#`）
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - インラインコメント（クォートなしの `#` が直前に空白/タブのときのみコメントとして扱う）
  - 自動ロード順序: OS 環境変数 > .env.local > .env（`.env.local` は上書き可能）。OS 環境変数を保護する仕組みあり。
  - 自動読み込み無効化環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 必須環境変数取得時は未設定で ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - `Settings` クラスで各種設定値をプロパティとして提供（DB パスのデフォルト、KABUSYS_ENV/LOG_LEVEL のバリデーション等）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX マーケットカレンダーの取扱い・夜間更新ジョブ `calendar_update_job` を実装。J-Quants クライアントを通した差分取得 → 冪等保存（ON CONFLICT 相当）を想定。
    - 営業日判定ユーティリティを提供: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。DB 登録がない場合は曜日（週末）フォールバックを行う。
    - 最大探索日数やバックフィル、健全性チェックを備えた安全設計。
  - ETL パイプライン（pipeline / etl）
    - ETL 結果を表す `ETLResult` データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧を保持）。
    - 差分更新・バックフィル戦略、品質チェック連携のための下地を実装。
    - `etl` モジュールはパブリックインターフェース（ETLResult）を再エクスポート。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリングする処理 `score_news` を実装。
    - 時間ウィンドウ計算（JST 基準 → DB は UTC 想定）`calc_news_window`。
    - チャンク処理（最大 20 銘柄／チャンク）、1 銘柄あたりの記事数・文字数上限、レスポンスバリデーション（JSON 解析、results 配列、code/score の検証）を実装。
    - リトライ／バックオフ（429・ネットワーク断・タイムアウト・5xx を対象）やフェイルセーフ（失敗時は該当チャンクをスキップし、他銘柄のデータを保護）を搭載。
    - DuckDB への書き込みは部分置換（DELETE → INSERT）で冪等性かつ部分失敗時の安全性を確保。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジームを判定する `score_regime` を実装。
    - マクロニュース抽出はキーワード（日本・米国系）でフィルタし、LLM（gpt-4o-mini）に JSON 出力を期待して評価。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - ルックアヘッド防止のため、クエリと処理で target_date 未満のデータのみを参照する設計を明示。
    - テスト用差し替えフックあり（_call_openai_api）。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER, ROE）、Volatility（20日 ATR）や流動性指標（20日平均売買代金、出来高比率）を DuckDB 上の SQL と Python ロジックで計算する関数群を実装:
      - `calc_momentum`, `calc_value`, `calc_volatility`
    - データ不足時は None を返す設計、結果は (date, code) をキーとする dict のリストを返す。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算 `calc_forward_returns`（可変ホライズン、入力検証あり）、ランク相関 IC（Spearman）を計算する `calc_ic`、ランク化ユーティリティ `rank`、統計サマリー `factor_summary` を実装。
    - 外部ライブラリに依存せず純粋な標準ライブラリ／DuckDB で完結する実装。

- 汎用 / 実装上の注意点
  - DuckDB を主要な分析 DB として使用（関数群は DuckDB 接続を受け取る設計）。
  - 各所で入力検証・NULL 安全・データ不足時のフォールバックを明確に実装（例: MA200 に足りない場合は中立値を返す等）。
  - OpenAI 呼び出しについては JSON parsing の冗長なケース（余分な前後テキスト）への復元処理を実装。
  - ログ出力（info/warning/exception）を多用し、異常時のトレーサビリティを確保。
  - テスト容易性のために一部内部 API（OpenAI 呼び出し等）を patch しやすい設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため特記事項なし。ただし OpenAI/API キーや機密情報は環境変数で管理する設計。

### Notes / Migration / 使用上の注意
- 必要環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
  - OPENAI_API_KEY（OpenAI 呼び出し。score_news / score_regime で必須）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テストなどで有用）。
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
- OpenAI モデルは現状 gpt-4o-mini を指定。JSON Mode を使用して厳密な JSON 出力を期待するため、レスポンス検証を行っています。
- すべての処理はルックアヘッドバイアスを避ける設計（内部で datetime.today()/date.today() を参照しない、target_date ベースで処理）。
- DuckDB の executemany の制約を考慮し、空リスト渡しを避ける処理を行っています（互換性確保）。
- J-Quants 等外部クライアント呼び出しには例外防御とログを多用し、失敗した場合は部分処理を維持する設計（フェイルセーフ）。
- 将来的な互換性・拡張のため、内部での OpenAI 呼び出し実装はモジュール間で共有しない方針（各モジュールで独立実装）。

---

注: 本 CHANGELOG はソースコードの内容から推定して記載しています。今後のリリースでは機能追加・修正・破壊的変更をそれぞれのバージョンセクションに追記してください。