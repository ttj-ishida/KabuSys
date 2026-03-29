# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
リリースはセマンティックバージョニングに従います。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・データ基盤向けのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを追加。__version__ = "0.1.0" を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - .git または pyproject.toml を基準にプロジェクトルートを探索し、CWD に依存しないファイル探索を実装。
  - .env 行パーサーは export 構文・引用文字列・インラインコメント等に対応。
  - 環境変数取得用 Settings クラスを提供（J-Quants, kabuステーション, Slack, DB パス, 実行環境/ログレベル判定など）。未設定の必須値は明示的に例外を投げる _require を実装。
  - 有効値チェック（KABUSYS_ENV, LOG_LEVEL）のバリデーションを実装。
  - デフォルトの DB パス（DuckDB/SQLite）を設定。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を基にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
  - 計算ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で明確に定義。
  - バッチ処理（最大 20 銘柄 / チャンク）、トークン肥大対策（記事数・文字数上限）、JSON レスポンスのバリデーション、スコアのクリップ（±1.0）を実装。
  - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。致命的ではない失敗時はスキップしてフェイルセーフに継続。
  - OpenAI 呼び出しを抽象化した private 関数を提供してテスト時のモック差し替えを容易化。
  - ai_scores テーブルへの冪等的な書き込み（DELETE → INSERT）を実装し、部分失敗時に既存データを保護する動作を採用。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする score_regime を実装。
  - マクロニュース抽出に使うキーワード群を定義。LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフを実装。
  - OpenAI クライアントの呼び出しは独立実装とし、モジュール間の結合を低減。
  - API リトライ（RateLimit・接続エラー・タイムアウト・5xx）とリトライ待機を実装。

- データ基盤（kabusys.data）
  - ETL インターフェース: pipeline.ETLResult を公開（kabusys.data.etl）。
  - ETL パイプラインの基本構造（差分更新、バックフィル、品質チェック、id_token の注入可能性）を定義する pipeline モジュールを実装。ETL 実行結果を表す dataclass ETLResult（品質問題・エラーの集約、辞書化サポート）を提供。
  - 市場カレンダー管理（calendar_management）:
    - market_calendar テーブルを基に営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API 経由でカレンダーを差分取得して保存（バックフィル、健全性チェック含む）。J-Quants クライアント呼び出しに対する例外捕捉とロギングを実装。
    - 最大探索日数やバックフィル・先読みに関するパラメータを定義して無限ループや極端値を防止。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金/出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数群（calc_momentum, calc_volatility, calc_value）を実装。
    - データ不足時の None ハンドリング、SQL による集計とウィンドウ関数利用、結果を (date, code) ベースの dict リストで返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）を任意ホライズンで実行。
    - IC（Information Coefficient）計算（スピアマンのランク相関）を calc_ic で実装。必要な有効レコード数チェック（3 件未満は None）を行う。
    - rank ユーティリティ（同順位の平均ランク、丸め処理により ties の誤検出を防止）。
    - factor_summary による各ファクター列の基本統計量（count/mean/std/min/max/median）計算。

- 汎用設計方針（全体）
  - ルックアヘッドバイアス防止のため、score_news / score_regime 等は datetime.today()/date.today() を直接参照しない設計（target_date を明示受け取り）。
  - DuckDB を永続層として利用し、executemany の空リスト問題や型変換に配慮した実装。
  - 外部 API 呼び出しは失敗時にシステム全体が停止しないようにフェイルセーフ（スキップ/デフォルト値）を採用。
  - 各所で詳細なログと警告を出力。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制約 / 注意点 (Known issues / Notes)
- OpenAI API キーは引数で注入可能だが、未設定の場合は環境変数 OPENAI_API_KEY を必須とする（未設定なら ValueError を送出）。
- DuckDB のバージョン差異（リスト型バインドの挙動など）に対する互換性考慮を行っているが、環境によって追加の調整が必要になる場合がある。
- 一部モジュールは jquants_client、kabu ステーション等外部クライアントに依存するため、本番連携には各 API クレデンシャル/エンドポイントの設定が必要。
- news_nlp と regime_detector は OpenAI 呼び出しの内部実装を意図的に分離しており、テスト時は各モジュール内の private 関数をモックする設計。

### セキュリティ (Security)
- 初期リリース。特にセキュリティ脆弱性の修正は無し。

---

参考: 各モジュール詳細はソースコード内 docstring に設計方針・処理フロー・エッジケースの取り扱いが記載されています。リリース後の修正や機能追加は次バージョンで追記します。