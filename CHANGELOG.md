CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ公開インターフェースを定義
  - src/kabusys/__init__.py にて __version__ と主要サブパッケージ（data, research, ai, ...）をエクスポート。
- 環境変数・設定管理
  - src/kabusys/config.py
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - export KEY=val 形式・クォート/エスケープ・行末コメントを考慮した .env パーサ実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得関数（_require）と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境種別/ログレベル判定等）。
  - 環境変数保護（OS 環境を上書きしない挙動）をサポート。
- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメントスコア算出。
    - チャンク（最大 20 銘柄）でのバッチ処理、トークン肥大化対策（記事数/文字数トリム）、詳細なレスポンスバリデーション。
    - 再試行（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフ、フェイルセーフ（API 失敗時はスキップして継続）。
    - DuckDB への書き込みは部分的置換（該当コードのみ DELETE → INSERT）で部分失敗による既存データ消失を防止。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window（JSTベースのニュース対象ウィンドウ）を提供。
  - src/kabusys/ai/regime_detector.py
    - ETF（1321）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス対策（内部で date.today() を参照しない設計、DB クエリに date < target_date を使用）。
- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）の計算関数を提供。
    - DuckDB 上で SQL とウィンドウ関数を活用して計算（prices_daily / raw_financials のみ参照）。
    - データ不足時の None ハンドリングとログ出力。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン fwd_1d 等）、IC（スピアマンのランク相関）計算、ランク関数、ファクター統計サマリーを提供。
    - pandas など外部依存せず、純粋 Python + DuckDB で実装。
  - src/kabusys/research/__init__.py に公開 API をまとめて再エクスポート。
- Data（データ基盤関連）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが無い場合は曜日ベースのフォールバック、DB の値を優先する一貫した挙動設計。
    - 夜間バッチ更新 job（calendar_update_job）と J-Quants クライアント連携（差分取得・バックフィル・健全性チェック）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラス（ETL 実行結果の集約）を実装し、pipeline モジュールから公開。
    - 差分更新・バックフィル・品質チェックを考慮した ETL 設計方針（jquants_client 経由の idempotent 保存、品質問題は収集して呼び出し元へ報告）。
    - DuckDB の互換性注意（executemany に空リストを渡せない制約を回避）。
- テスト/運用に役立つフック・設計上の配慮
  - OpenAI 呼び出しをモック可能（_call_openai_api の差し替え）。
  - ルックアヘッドバイアスを防ぐ設計（日付の扱いを明示、target_date を入力として洗練されたウィンドウ計算）。
  - エラー発生時は例外を無闘に投げるのではなくログ警告とフォールバック（安全第一のフェイルセーフ）を多用。
  - DuckDB を前提とした実装で互換性（date 型変換や executemany の扱い）に配慮。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OpenAI 等）は引数注入 or 環境変数で解決（明示的に未設定時は ValueError を発生させ安全性を確保）。
- .env 自動ロード時に OS 環境変数を上書きしない保護機構を実装。

注意事項（既知の挙動・設計メモ）
- OpenAI の API 呼び出し失敗時は多くの場合フォールバック（スコア 0.0 またはスキップ）し、処理を継続します。アプリケーションの要件によっては呼び出し元で厳密な失敗判定を行ってください。
- DuckDB のバージョン依存の挙動（executemany に空リストを渡せない等）に対応するため、空パラメータ時は処理をスキップするガードを設けています。
- news_nlp と regime_detector は内部で別々に OpenAI 呼び出しヘルパーを持ち、モジュール結合を避けるよう設計しています（テスト容易性のため）。

今後の予定（含めたい機能例）
- 実行（execution）・監視（monitoring）サブパッケージの実装拡充（売買実行ロジック・Slack 通知等）。
- ETL の品質チェックルール追加および自動修復オプション。
- モデルのオンプレ/ローカル LLM 対応、あるいは OpenAI API 呼び出しのコスト最適化。
- ドキュメント（Usage / API / Data Schema）の拡充。

---
この CHANGELOG はコードベースから機能と設計方針を推測して作成したものです。実際のリリースノート作成時はリリース日、著者、マイナーな変更点などを適宜補完してください。