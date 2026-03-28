CHANGELOG
=========

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の慣例に従っており、セマンティックバージョニングを採用しています。

Unreleased
----------

Added
- ドキュメントとログの強化候補を追加（今後のリファクタで詳細ログやメトリクスを追加予定）。
- 非同期版 OpenAI クライアントや追加モデル（例: gpt-4 系列）対応の検討を追記。

Changed
- —（現時点で未リリースの変更点のプレースホルダ）

Fixed
- —（現時点で未リリースの修正のプレースホルダ）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ初期エントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン情報 (__version__ = "0.1.0") を定義。

- 環境設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサを実装（export 形式・クォート・バックスラッシュエスケープ・インラインコメント対応）。
  - 必須環境変数チェックを提供（_require）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境等のプロパティを公開。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
  - duckdb/sqlite のパスを Path 型で取得するヘルパーを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news, news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini、JSON mode）にバッチ送信してセンチメントを算出。
    - タイムウィンドウ計算（JST ベース → UTC 変換）を実装（calc_news_window）。
    - バッチ処理（_BATCH_SIZE=20）、記事数/文字数上限、スコアクリップ（±1.0）、レスポンスバリデーションを実装。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）とエクスポネンシャルバックオフを実装。
    - 部分失敗時に既存スコアを保護するため、対象コードのみを DELETE → INSERT する冪等的書き込みを実装。
    - DuckDB の制約を考慮し executemany の空リスト送信を回避するガードを実装。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算するロジック（_calc_ma200_ratio）。
    - raw_news からマクロキーワードで記事を抽出するロジック（_fetch_macro_news）。
    - OpenAI 呼び出し（gpt-4o-mini、JSON mode）とマクロスコア取得のリトライ/フォールバック実装（_score_macro）。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - レジーム合成、閾値によるラベル付け、market_regime への冪等書き込みを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比）やバリュー（PER、ROE）を DuckDB ベースで計算。
    - 関数: calc_momentum(conn, target_date)、calc_volatility(conn, target_date)、calc_value(conn, target_date) を提供。
    - データ不足時の None ハンドリング、営業日スキャンのバッファ設計を実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンへの将来リターンを一括 SQL で取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランク化ユーティリティ rank）を実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - pandas 等非依存・標準ライブラリのみで実装。

- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバックを採用。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等保存。バックフィルと健全性チェックを実装。
    - 最大探索日数やバックフィル期間などの安全制約を導入。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得ロジック、保存（jquants_client 経由で冪等保存）、品質チェック結果（quality モジュール連携）の収集を支援するユーティリティを実装。
    - DuckDB テーブル存在確認や最大日付取得ユーティリティ等を提供。

- 内部設計方針・安全対策（全体）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() をコア処理で直接参照しない設計（target_date を外部から注入する方式を採用）。
  - OpenAI 呼び出しでは JSON mode を利用し、レスポンスの厳密検証とフォールバックを行う。
  - LLM/API 呼び出しの堅牢化（リトライ、指数バックオフ、5xx と非5xx の扱い区別）。
  - DB 書込みは冪等性を確保（DELETE → INSERT／ON CONFLICT の利用想定）。
  - DuckDB のバージョン互換性考慮（executemany の空リスト禁止回避や型変換処理など）。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- OpenAI API キーは引数での注入または環境変数 OPENAI_API_KEY を参照する実装。キー未設定時は ValueError を発生させる（誤使用を抑止）。

Notes / Known limitations
- 外部依存（OpenAI, J-Quants, kabuステーション）は抽象化されているが、実行には各種 API キーと実際の DB（DuckDB）スキーマが必要。
- JSON パースや LLM レスポンスの不確実性に備え、スコア計算はフェイルセーフ（多くの場合 0.0 やスキップ）となるため、部分的なデータ欠損時にも他処理を保護する設計です。
- パフォーマンス面では DuckDB による SQL 集約を多用しているが、大規模データでの検証や最適化（インデックス・パーティショニング等）は今後検討が必要。

License
- —（パッケージのライセンス表記が別途ある場合はそちらを参照してください）

README やドキュメントに記載する予定の項目
- セットアップ手順（.env.example、必要な環境変数一覧）
- DuckDB の推奨スキーマ/テーブル定義（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等）
- 実運用時の注意点（API レート、コスト、スケジューリング、監視）
- テストおよび開発用の環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD など）

もし特定の変更点（リリース日や追加で記載したい項目）があれば教えてください。CHANGELOG をその内容に合わせて更新します。