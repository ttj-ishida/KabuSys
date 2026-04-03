CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

v0.1.0 — 2026-04-03
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - 公開サブパッケージ: data, research, ai, monitoring（__all__ には data, strategy, execution, monitoring を定義）。

- 環境設定/ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ロード機能を提供。
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索してルートを特定。ルートが見つからない場合は自動ロードをスキップ。
  - .env パーサ実装: export 形式・クォート・エスケープ・インラインコメントに対応する堅牢な行パース実装。
  - 自動ロード設定の無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護: OS 環境変数を protected として .env.local の上書きから保護。
  - Settings クラスを提供（settings インスタンスで利用可能）:
    - J-Quants / kabu API / LINE / DB パス（duckdb/sqlite）/監視用ファイルパス/閾値などのプロパティを提供。
    - env / log_level のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込み。
  - スコア収集の時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
  - バッチ処理: 最大 20 銘柄 / コールでバッチ送信。1銘柄あたりは記事数・文字数（デフォルト最大 10 記事、3000 文字）でトリム。
  - JSON Mode の応答検証: レスポンスの JSON パースと results フォーマット検証。未知コードや不正なスコアは無視。
  - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。失敗時は個別チャンクをスキップして処理継続（フェイルセーフ）。
  - DuckDB 0.10 の executemany 制約に合わせ、空パラメータ回避ロジックを実装。
  - テスト容易性: OpenAI 呼び出し関数を内部で分離して unittest.mock により差し替え可能。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull / neutral / bear）。
  - マクロ記事は raw_news からマクロキーワードでフィルタ（キーワード一覧を実装）。
  - OpenAI を gpt-4o-mini（JSON 応答）で呼び出し、冗長なエラーハンドリングと最大リトライを備えた実装。
  - レジームスコアはクリップ（-1.0〜1.0）し、market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
  - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
  - テスト用フック: _call_openai_api を差し替え可能にしてテストを容易に。

- データプラットフォーム（src/kabusys/data/*）
  - マーケットカレンダー管理（calendar_management.py）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants からの差分取得と market_calendar への冪等保存を想定。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - DB 未登録時は曜日ベースのフォールバック（週末非営業日）を提供し、DB 登録値を優先する一貫したロジックを実装。
    - 探索上限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェック（将来日付異常のスキップ）を実装。
  - ETL パイプライン（pipeline.py, etl.py）
    - 差分更新・保存・品質チェックを行う ETLResult データクラスを公開（ETLResult は etl.py 経由で再エクスポート）。
    - ETLResult に品質問題のサマリ・エラー有無判定・辞書化ユーティリティを実装。
    - 差分ロード、backfill、IDEMPUTENT 保存（jquants_client の save_* 関数を想定）および品質検査（quality モジュール連携）の設計方針を盛り込む。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装（パイプライン内部で使用）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数群を実装。
    - DuckDB SQL を用いた一括計算設計。データ不足時は None を返す堅牢実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換（rank）、要約統計量（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - calc_ic はスピアマンのρ（ランク相関）を計算。3 件未満で計算不可は None を返す。

- 実装上の設計ポリシー・ユーティリティ（共通）
  - ルックアヘッドバイアス回避: datetime.today()/date.today() をアルゴリズム内部で直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主要なデータレイヤとして採用し、SQL と Python の併用で高速集計を実現。
  - OpenAI API 呼び出しは JSON Mode を前提に応答バリデーションを徹底。
  - API 呼び出しの失敗に対するフォールバック（ゼロスコアやスキップ）を各モジュールで実装し、フェイルセーフを重視。
  - テスト容易性を意識して API 呼び出し箇所を差し替え可能に設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 環境変数の取り扱いに注意:
  - OpenAI / J-Quants / KabuStation 等のシークレットは環境変数経由で提供。Settings は必須キー未設定時に ValueError を発生させることで明示的に扱う。
  - .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト等での安全対策）。

Notes
- このリリースは機能初期実装に相当します。データベーススキーマ（prices_daily, raw_news, ai_scores, market_calendar, market_regime, raw_financials 等）は外部ドキュメント（DataPlatform.md / StrategyModel.md）に準拠している想定です。
- OpenAI 利用箇所（news_nlp/regime_detector）は外部 API のエラーやコストを考慮しており、運用時は API キー管理・レート制御・コスト監視を推奨します。