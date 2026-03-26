# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
このファイルはコードベースの現状（ソースから推測可能な実装・設計）に基づき作成しています。

フォーマット:
- 変更はカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）ごとにまとめています。
- 各項目はモジュール名や関数名、挙動の要点を明記しています。

※ バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]
- 次期リリースでの改善候補（ソースから推測）
  - OpenAI クライアント初期化・認証の抽象化（テスト容易性向上）。
  - News / Regime の LLM プロンプト最適化と追加のレスポンス検証ルール。
  - ETL の差分取得ロジックでのより細かい並列化・メトリクス収集。
  - calendar_update_job のより詳細な監査ログ・メトリクス追加。

## [0.1.0] - 2026-03-26
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージメタ情報および公開 API を定義（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開対象として設定。

- 環境設定・ロード
  - .env / .env.local の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点）。
    - .env と .env.local の読み込み順序（OS 環境 > .env.local > .env）をサポート。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
    - OS 環境変数を保護する protected キーの概念を導入（.env による上書きを制御）。
    - .env の各行パーサーは export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを実装しアプリ設定をプロパティで提供（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル検証など）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。
    - DuckDB / SQLite のデフォルトパスを Path として返す。

- AI モジュール（LLM 統合）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - gpt-4o-mini（JSON Mode）を用いたセンチメントスコア取得。
    - 1 チャンクあたり最大 20 銘柄のバッチ送信、1銘柄あたり記事数と文字数の制限（トリム）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフとリトライ。
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code のマッチング、数値チェック）、スコア ±1.0 でクリップ。
    - 書き込みは idempotent な削除→挿入（DELETE → INSERT）で実装し、部分失敗時に他銘柄の既存スコアを保護。
    - テスト用に _call_openai_api の差し替えを想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を判定・保存。
    - マクロニュースはニュース NLP の窓（calc_news_window による）で抽出、LLM 呼び出しで macro_sentiment を取得。
    - API エラー時は macro_sentiment=0.0 にフェイルセーフフォールバック。
    - OpenAI 呼び出しに対するリトライ処理（429/接続/タイムアウト/5xx）を実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。失敗時は ROLLBACK を試行。

- データ基盤（DuckDB ベース）
  - ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass による ETL 実行結果の集約（品質問題・エラーを含む）。
    - テーブル存在確認、最大日付取得等のユーティリティを実装。
    - 差分更新、バックフィル、品質チェックの設計を反映（実装の骨子）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job を実装し J-Quants からの差分取得 → 保存（バックフィルと健全性チェック含む）を実行。
    - 最大探索日数やバックフィル日数、先読み設定などを定義。
  - jquants_client 連携想定（モジュール参照あり、クライアント実装は別モジュール）。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB SQL ベースで計算。
    - データ不足時の None 戻しやログを実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク化ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部ライブラリ依存なしでアルゴリズム実装。

### Changed
- （初期リリース相当の実装方針の明示）
  - ルックアヘッドバイアス回避のため、すべてのモジュールで datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示引数として受ける）。
  - DuckDB 操作の互換性を考慮（executemany の空リスト回避など）した実装。

### Fixed
- .env パーサーの強化（コメント・クォート・エスケープ処理）により誤読の低減。
- OpenAI レスポンスの JSON パース失敗時に前後テキストが混入していても中括弧から抽出を試みる耐性強化（news_nlp）。

### Security
- 環境変数ロード時に OS 環境（既存の env）を protected として扱い、.env による意図しない上書きを防止。

### Notes / Implementation details
- OpenAI 呼び出しは openai.OpenAI クライアントを直接生成（api_key を引数または環境変数 OPENAI_API_KEY から取得）。テストしやすいように内部の _call_openai_api をモック可能に設計。
- LLM への入力は JSON Mode（response_format={"type": "json_object"}）を想定し、レスポンスの安全なパースと検証に重点を置く。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT を想定する保存関数の利用）。
- DuckDB を主要な分析・格納エンジンとして使用。パスは環境変数で上書き可能（デフォルトは data/kabusys.duckdb 等）。

---

以上がソースコードから推測して作成した CHANGELOG.md です。追加でリリース日や担当者・リリースノートの追記、あるいは各機能の使用例や制限事項を CHANGELOG に加えたい場合は指示を出してください。