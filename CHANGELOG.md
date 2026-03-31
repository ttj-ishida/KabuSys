CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。
主にソースコードから推測できる追加機能・挙動・設計方針を記載しています。

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージの初期公開 (kabusys v0.1.0)
  - パッケージメタ情報: __version__ を "0.1.0" に設定。
  - 公開モジュール: data, strategy, execution, monitoring をパッケージレベルからエクスポート。

- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式、クォート・エスケープ、インラインコメント処理などに対応した .env パーサを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、J-Quants・kabuステーション・Slack・DBパス・監視設定・システム設定（環境・ログレベル）等を環境変数から取得・検証するプロパティを提供。
  - 環境変数未設定時に明確な ValueError を投げる _require 実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、1銘柄あたりの記事数・文字数制限（トリム）を実装。
    - OpenAI 呼び出しに対するリトライ（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフを実装。
    - JSON Mode のレスポンスのバリデーション・パース耐性（前後余計テキストの復元）を実装。
    - DuckDB に対する冪等書き込み（DELETE → INSERT、executemany の空チェック）を実装。
    - calc_news_window により JST ベースのニュースウィンドウ計算を提供（前日 15:00 JST ～ 当日 08:30 JST の UTC 換算）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロ経済ニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみを使用しルックアヘッドを防止）、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - OpenAI API 呼び出しのリトライ／エラーハンドリングと、失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部の _call_openai_api を patch 可能）。

- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの有無に応じた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、探索上限の導入による安全性確保。
    - JPX カレンダーの差分取得・夜間バッチ更新 job (calendar_update_job) を実装（J-Quants クライアント経由でフェッチ→保存、バックフィル、健全性チェック）。

  - ETL パイプライン関連（kabusys.data.pipeline, etl）
    - ETLResult データクラス（取得数・保存数・品質問題・エラー等の集約）を公開。
    - 差分更新・バックフィル・品質チェックに関する設計方針をコードに反映（J-Quants クライアント呼び出しポイントを想定）。
    - テーブル存在確認／最大日付取得等のユーティリティを実装（DuckDB 前提）。

  - データ抽象化ポイント（kabusys.data.etl）で ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の SQL を用いて計算する関数を実装。
    - データ不足の際の None 扱い、営業日ベースのホライズン設計、ログ出力を実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリ不使用（標準ライブラリのみ）での統計実装、入力検証（horizons の制約）を実装。

- 共通設計/実装方針
  - ルックアヘッドバイアス回避: 日付計算で datetime.today()/date.today() を直接参照しない（target_date ベース）。
  - DuckDB を主要なデータストアとして想定した SQL 実装。
  - API 呼び出しに対する安全策（リトライ、バックオフ、失敗時フォールバック、ログ出力）を徹底。
  - 冪等な DB 書き込みパターン（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK によるトランザクション制御）を採用。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 環境変数取得に対する必須チェック（_require）を実装し、未設定時に明確な例外を返すことで秘密情報未設定の検出を容易化。

Notes / 備考
- コード内で参照される外部クライアント（J-Quants クライアント、OpenAI クライアント、kabu API など）はモジュール分離されており、抽象化レイヤー経由で呼び出す設計になっています（実体は別モジュールで実装する想定）。
- DuckDB 固有の挙動（executemany の空リスト制約等）を考慮した実装になっています。
- OpenAI のレスポンスパースは堅牢化されているものの、モデル仕様の変化に対する互換性維持のためレスポンス検証は重要です。

今後の検討事項（推奨）
- ai モジュールでのテスト用のモックフックの拡充（注入可能な sleep/クライアント/モデル指定など）。
- ETL の品質チェック結果に基づく運用アクションやアラート連携（Slack 等）を追加。
- k8s 等での監視用に pid ファイル以外のプロセス監視・メトリクス出力機能の追加。

---