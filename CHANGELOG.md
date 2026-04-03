# Changelog

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

テンプレートの説明:
- Unreleased: 今後の変更予定（このリポジトリの現在のスナップショットに基づく推測を記載）
- 各リリースは日付付きで記載

## [Unreleased]

予定・注意点（コードから推測）
- 実行（execution）・監視（monitoring）パッケージは __all__ に含まれているが、今回のスナップショットでは実装ファイルが含まれていないため、これらの公開 API 実装の追加やドキュメント整備が今後必要。
- テスト用のモックや CI ワークフロー（OpenAI クライアント、DuckDB を用いた統合テストなど）の整備が望ましい（現状、OpenAI 呼び出しは実行時の外部依存）。
- 秘匿情報の取り扱い・運用手順（.env 管理、KABUSYS_DISABLE_AUTO_ENV_LOAD の運用）を README に具体例として追加予定。

---

## [0.1.0] - 2026-04-03

初回リリース（コードベースの現状をもとに推測してまとめた主要機能群）

Added
- 基本パッケージ:
  - pakage 名称: `kabusys`、バージョン `0.1.0` を定義（src/kabusys/__init__.py）。
  - 暫定公開モジュール: data, strategy, execution, monitoring（__all__ に列挙）。
- 環境設定管理:
  - `kabusys.config.Settings` を追加し、環境変数から各種設定（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログレベル など）を取得するプロパティを提供。
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーの実装: export 形式対応、クォート内のバックスラッシュエスケープ処理、コメント（#）取り扱いなどに対応。
  - 必須環境変数未設定時に明確なエラーメッセージを出す `_require` を追加。
  - `env` / `log_level` の値検証（許容値チェック）を追加。
- AI（NLP）機能:
  - `kabusys.ai.news_nlp.score_news`:
    - raw_news と news_symbols を用いた銘柄別ニュース集約、OpenAI（gpt-4o-mini）へバッチ送信、JSON Mode 応答パース、スコアのクリップ、DuckDB への冪等書き込みを実装。
    - ウィンドウ定義（JST基準）を提供する `calc_news_window` を実装（ルックアヘッドバイアス回避のため date.today() を直接参照しない）。
    - バッチサイズ、最大記事数、トークン肥大化対策（記事トリム）、リトライ（指数バックオフ）、エラーハンドリングを備える。
    - レスポンスの堅牢なバリデーションと部分書き込み保護（取得成功した銘柄のみ DELETE → INSERT）を実装。
  - `kabusys.ai.regime_detector.score_regime`:
    - ETF（1321）の200日MA乖離とマクロニュースのLLMセンチメントを重み合成して市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロニュースの抽出（キーワードフィルタ）／OpenAI 呼び出し／リトライ／フォールバック（API失敗時は 0.0）を実装。
    - モジュール間の結合を避ける設計（OpenAI 呼び出し用の内部関数を別実装）。
- Data プラットフォーム（DuckDB ベース）:
  - `kabusys.data.pipeline.ETLResult` と ETL 基盤の骨組み（差分取得、バックフィル、品質チェックの枠組み）を実装。ETL 結果を表す dataclass とユーティリティを提供。
  - `kabusys.data.etl` で ETLResult を再エクスポート。
  - `kabusys.data.calendar_management`:
    - market_calendar を扱う営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチ `calendar_update_job` を実装。バックフィル、健全性チェック、API 呼び出し例外処理を実装。
  - DB テーブル存在チェック等のユーティリティを整備。
- Research（因子研究）:
  - `kabusys.research.factor_research`:
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。prices_daily / raw_financials を参照し、モメンタム（1/3/6M）、MA200乖離、ATR20、出来高・売買代金の指標、PER/ROE などを計算。
    - SQL ウィンドウ関数を多用し、データ不足時の None 扱いなど堅牢性を確保。
  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns`, `calc_ic`, `rank`, `factor_summary` を実装。外部ライブラリに依存せず標準ライブラリのみで統計量・ランク相関を計算。
    - `rank` 実装では浮動小数の丸め（round）で ties を安定処理。
  - `kabusys.research.__init__` で主要関数を再エクスポート。
- ロギング/エラーハンドリング:
  - 各所で logger を使用し、重要な警告・例外・処理完了ログを出力。
  - DB 書き込みは明示的なトランザクション（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK を組み合わせた冪等実装。

Changed
- OpenAI 呼び出しの設計:
  - 各 AI モジュールで独自の `_call_openai_api` を用意し、モジュール間のプライベート関数共有を避けて結合度を低くした。
- JSON パースの堅牢化:
  - news_nlp/regime_detector のレスポンス処理で、JSON 前後に余剰テキストが混入している場合に最外の {} を抽出してパースするなど、実運用で起き得る不正形式に耐性を持たせた。
- Look-ahead バイアス対策:
  - AI スコアリングやレジーム判定、ETL/研究関数で date.today / datetime.today を直接参照せず、明示的な target_date を受け取る設計に統一。

Fixed
- DuckDB の互換性ワークアラウンド:
  - executemany に空リストを渡せないバージョン問題に対処し、空の場合は実行をスキップするガードを追加（score_news の書き込み処理など）。
- 環境変数パーサー (_parse_env_line):
  - export プレフィックス、クォート内のバックスラッシュエスケープ、コメント取り扱いの改善により .env ファイルの実用性を向上。
- API エラー・ネットワーク断へのリトライ実装:
  - OpenAI への呼び出しで RateLimit / 接続エラー / タイムアウト / 5xx を対象に指数バックオフで再試行し、最終的にフェイルセーフ（0.0 戻し）する処理を実装。

Security
- 環境変数取り扱い:
  - OS 環境変数を _load_env_file の protected 引数で保護し、.env による既存環境の上書きを防止する仕組みを導入。

Notes / Limitations
- 実行時依存:
  - OpenAI クライアントおよび J-Quants クライアント（jquants_client）は実行時に外部 API を呼び出すため、運用環境での API キー管理とネットワークアクセスが必要。
- 未実装 / 要配置:
  - strategy / execution / monitoring の具体実装ファイルは今回のスナップショットに含まれていない。アルゴリズム実装や発注ロジック、プロセス監視の追加が必要。
- テスト:
  - OpenAI 呼び出しは unittest.mock.patch による差し替えを想定した設計になっているが、統合テストの整備が望ましい。

---

（注）上記は提供されたソースコードの内容から推測して整理した CHANGELOG です。実際のリリース履歴や日付・詳細はリポジトリ運用ルールに合わせて調整してください。