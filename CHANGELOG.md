# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

- ドキュメント・設計注記の追加: モジュールごとの設計方針やフェイルセーフ動作、ルックアヘッドバイアス防止方針（datetime.today/date.today を直接参照しない）が各モジュールに明示されました。
- テスト容易性の向上: OpenAI 呼び出しを行う内部関数（例: _call_openai_api）を unittest.mock.patch で差し替え可能とする実装注記／構造を追加しました。
- DuckDB 互換性と安全性向上: executemany に空リストを渡さないチェック、日付型変換ユーティリティ、部分失敗時に既存データを保護する置換（DELETE → INSERT）などの実装方針を整備しました。

## [0.1.0] - 2026-03-27

### Added
- 初回リリース。以下の主要機能を実装・公開。
- パッケージ初期化
  - kabusys パッケージ初期化（src/kabusys/__init__.py）: バージョン情報と主要サブパッケージのエクスポートを追加。

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - .git / pyproject.toml を基準にプロジェクトルートを探索して .env/.env.local を読み込む自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - export KEY=val 形式・クォート（シングル／ダブル）内のエスケープ処理・インラインコメント処理に対応した行パーサを実装。
  - OS 環境変数を保護する protected 機構と override オプションを実装。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス・実行環境（development/paper_trading/live）・ログレベル等の取得メソッドを実装（必須値未設定時は ValueError を発生）。

- AI モジュール（src/kabusys/ai）
  - ニュースNLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を評価。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンスの厳密なバリデーション、スコアのクリップ、取得スコアのみを ai_scores テーブルへ置換する冪等書き込みを実装。
    - calc_news_window（JST 基準の時間ウィンドウ計算）を実装。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - マクロニュース抽出、OpenAI 呼び出し、指数バックオフリトライ、API 失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - 外部 API キー注入（引数 or 環境変数 OPENAI_API_KEY）に対応。

- データ処理 / ETL（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得、idempotent な保存（jquants_client 経由の保存関数呼び出し）、品質チェックの統合設計。
    - ETLResult データクラスを実装（取得数・保存数・品質問題一覧・エラー集約など）。
    - テーブル存在確認や最大日付取得ユーティリティを実装。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB データ優先・未登録日は曜日ベースのフォールバック、最大探索日数制限、バックフィルと健全性チェック、JPX カレンダー差分取得バッチ（calendar_update_job）を実装。

  - ETL 公開インターフェース（src/kabusys/data/etl.py）
    - pipeline.ETLResult の再エクスポート。

- リサーチ・ファクター（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高変化率）、Value（PER、ROE）などのファクター計算を実装。DuckDB を用いた SQL 中心の実装でルックアヘッドを防止。
  - feature_exploration.py
    - 将来リターンの一括取得（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、rank/統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージの __all__ を整備して主要ユーティリティを公開。

- データユーティリティ
  - 日付変換・DuckDB 互換性ユーティリティ、WINDOW 関連のスキャンバッファ、各種定数を整備。

### Changed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- OpenAI API キーはコード内にハードコードせず、引数または環境変数 OPENAI_API_KEY から取得する仕様にしています。

---

注:
- 多くのモジュールでは「ルックアヘッドバイアス防止」「部分失敗時のデータ保護」「冪等な DB 書き込み」「API エラーに対するフォールバック」を明示的な設計方針として採用しています。将来のリリースではこれらを継続して改善していく予定です。