# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システムの基盤モジュール群を実装しました。主要な追加点と設計上の注意点を以下に示します。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - 公開サブパッケージとして data, strategy, execution, monitoring を __all__ に定義（strategy/execution/monitoring の具象実装は別途）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を順次読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - 環境変数保護機能: OS 環境変数を protected として .env 上書きから保護。
  - 必須キー取得用 _require 関数、環境値検証（KABUSYS_ENV、LOG_LEVEL 等）。
  - 各種設定プロパティ: J-Quants / kabu API / Slack / DB パス / 監視阈値 等。

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）、JSON mode を想定した厳密なレスポンスバリデーション。
    - 再試行（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフ。
    - DuckDB への冪等書き込み（DELETE → INSERT）、部分失敗時に他コードの既存スコアを保護する設計。
    - パブリック API: score_news(conn, target_date, api_key=None) → 書込件数を返す。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST ベースのウィンドウを UTC naive datetime として返す）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - OpenAI 呼び出しは独自実装でテスト差し替え可能。
    - 再試行・フェイルセーフ（API 失敗時 macro_sentiment = 0.0）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - パブリック API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- データプラットフォーム (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを基に営業日判定/is_sq_day/next/prev/get_trading_days 等のユーティリティを実装。
    - DB データが不完全な場合は曜日ベースのフォールバック（週末判定）を行い、一貫性を保つ設計。
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ calendar_update_job を実装（バックフィル、健全性チェックあり）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装（取得・保存件数、品質問題、エラーの集約）。
    - pipeline 内部ユーティリティ（テーブル存在確認・最大日付取得など）を実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client など外部クライアント連携用フックを想定（実体は別モジュール）。

- 研究用モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、20 日 ATR（atr_20 / atr_pct）、流動性（avg_turnover / volume_ratio）、バリュー（PER, ROE）などを DuckDB 上で計算する関数を実装。
    - 公開関数: calc_momentum, calc_volatility, calc_value（それぞれ target_date を受け DuckDB の prices_daily / raw_financials を参照）。
    - データ不足時は None を返す等、安全なハンドリング。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン、バリデーションあり）。
    - IC（Spearman ρ）計算 calc_ic、ランク化ユーティリティ rank、統計サマリ factor_summary。
    - pandas 等外部依存を使わず純標準ライブラリ + DuckDB で実装。

### 変更 (Changed)
- 初回リリースのため変更履歴は特になし（初回導入機能の記録）。

### 修正 (Fixed)
- 各モジュールで運用上の堅牢性を重視した実装を導入:
  - OpenAI 呼び出しでの各種例外（RateLimitError / APIConnectionError / APITimeoutError / APIError）に対するリトライとフォールバックを実装。JSON パース失敗時も安全に 0.0 やスキップで継続。
  - DuckDB の executemany に関する互換性問題を考慮し、空リストを渡さないガードを追加。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等処理を行い、ROLLBACK 失敗時はログ出力して上位に例外を伝播。

### 注意 / 既知の制限 (Notes / Known issues)
- OpenAI 連携は gpt-4o-mini を想定したプロンプト設計および JSON Mode の応答に依存している。プロバイダ側のレスポンス仕様変更に注意。
- score_news / score_regime は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出する。
- .env パーサは一般的なシェル形式に対応しているが極端に複雑なケースでは動作しない可能性がある。
- strategy / execution / monitoring の具象実装はリリース対象外（インターフェース想定済み）。
- ルックアヘッドバイアス防止のため各処理は datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す必要あり）。

### セキュリティ (Security)
- .env の自動ロード時に既存の OS 環境変数を保護する仕組みを導入（.env で OS の秘密情報を上書きしないよう保護）。
- 環境変数が未設定のまま必須値を参照しようとした場合は明確なエラーメッセージを送出する（秘密情報の欠落検出を容易に）。

---

今後の予定（想定）
- strategy / execution / monitoring の具体実装追加。
- jquants_client の具体実装と ETL の統合動作確認テスト。
- 単体テスト / CI の整備、外部 API モック化によるテスト容易性向上。