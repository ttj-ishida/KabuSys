# Keep a Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

※この CHANGELOG はソースコードの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

Added
- パッケージ初期リリース。
- パブリック API / モジュール:
  - kabusys.config
    - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定時に設定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / データベース / 実行環境設定をプロパティで取得。
    - 必須環境変数未設定時に分かりやすい ValueError を送出する _require を実装。
    - env/log_level の入力検証および is_live/is_paper/is_dev のユーティリティを提供。
    - OS 側の既存環境変数は protected として上書きを防止。
  - kabusys.ai
    - news_nlp モジュール
      - raw_news と news_symbols を入力に OpenAI（gpt-4o-mini）でニュースごとのセンチメントを算出し、ai_scores に書き込む機能を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算（calc_news_window）。
      - バッチ処理（最大 20 銘柄／リクエスト）、トークン肥大化対策（記事数・文字数の上限）。
      - JSON Mode を想定した厳密なレスポンス検証（_validate_and_extract）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理。
      - DuckDB 互換性を考慮した部分的な DELETE → INSERT による冪等書き込み。
      - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - regime_detector モジュール
      - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
      - prices_daily/raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - LLM 呼び出しは失敗時に macro_sentiment=0.0 とするフェイルセーフ実装。
      - OpenAI API 呼び出しに対するリトライとエラー判定（5xx 再試行など）を実装。
      - 外部依存を減らすため、news_nlp の内部関数を共有せず独立実装。
  - kabusys.data
    - calendar_management モジュール
      - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB データがない/未登録の日は曜日ベースでフォールバックする設計。
      - カレンダー更新ジョブ calendar_update_job を実装（J-Quants API との差分取得、バックフィル、健全性チェック、冪等保存）。
    - pipeline / etl
      - ETLResult データクラスと ETL パイプライン用ユーティリティを公開。
      - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
      - DuckDB の日付取得/テーブル存在チェック等のユーティリティを実装。
  - kabusys.research
    - factor_research モジュール
      - 定量ファクター（モメンタム、バリュー、ボラティリティ／流動性）計算を実装（calc_momentum, calc_volatility, calc_value）。
      - prices_daily / raw_financials を用いた SQL+Python 実装。結果は (date, code) をキーとする dict リストで返却。
      - 200 日移動平均や ATR 計算などデータ不足時の None 扱い等の仕様を明記。
    - feature_exploration モジュール
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary といった統計・評価用関数を実装。
      - 依存は標準ライブラリ（pandas 等は使用しない）で実装。
  - パッケージ初期公開インターフェースとして各モジュールを __all__ で整備。
  - DuckDB を主要なローカル DB として利用する設計（型互換や executemany の制約への配慮あり）。

Security / Safety
- OpenAI キーの取り扱い:
  - API キーは関数引数で注入可能（テスト容易性・安全性を優先）。
  - 環境変数 OPENAI_API_KEY を代替として参照。
- .env ローダーは OS 側既存環境変数を保護（protected set）する挙動。
- モデル呼び出しでの失敗時は例外を無闘発生させずフェイルセーフ（スコア 0.0 など）として継続する設計が多く採用されている。

Other notable implementation details
- ルックアヘッドバイアス防止の方針:
  - score_news / score_regime 等の処理で datetime.today() / date.today() を直接参照せず、常に target_date を明示的に与える設計。
  - DB クエリで date < target_date のような排他条件を用いて将来データ参照を防止。
- OpenAI のレスポンスは JSON モードを用いる前提だが、実際に余計な前後テキストが混ざる可能性に備えて復元ロジックを持つ。
- DuckDB のバージョン依存（executemany の空リスト不可など）を考慮した実装がされている。
- ロギング、警告メッセージを豊富に出力して運用・デバッグを容易にしている。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- （特別なセキュリティ修正は今回の初回リリースには含まれないが、環境変数保護等の配慮あり）

---

注記:
- この CHANGELOG はリポジトリのソースコードから機能・設計・挙動を推測して作成しています。実際のリリースノート作成時は、コミットログやリリース担当者の記録と照合してください。