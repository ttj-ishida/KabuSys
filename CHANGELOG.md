KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-27

初回リリース。以下の主要機能と設計方針を実装しました。

### Added
- パッケージ基本構成
  - パッケージ名: kabusys、公開モジュール: data, research, ai, などを __all__ でエクスポート。
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数からの自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - 行中コメント処理（クォートなしの場合は '#' の前が空白/タブならコメントとして扱う）
  - _load_env_file にて既存 OS 環境変数を保護する protected 引数を導入し、override 動作を制御。
  - Settings クラスを提供しアプリケーション設定値にプロパティ経由でアクセス可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定取得（未設定時は ValueError）
    - データベースパス設定のデフォルト（DuckDB: data/kabusys.duckdb, SQLite: data/monitoring.db）
    - 環境モード（development, paper_trading, live）とログレベルの検証
    - 環境判定ユーティリティ: is_live / is_paper / is_dev

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信しセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（同時最大銘柄数 _BATCH_SIZE=20）と 1 銘柄あたりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用した厳密な JSON 出力期待とレスポンスのバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ処理。その他エラーはスキップして継続（フェイルセーフ）。
    - DuckDB の制約（executemany に空リスト不可）を考慮して書き込み前に空チェック。
    - テスト用フック: _call_openai_api を patch 可能にしユニットテストで差し替え可能。
    - calc_news_window により JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC naive datetime で算出。
    - API キー未設定時は ValueError を送出。
    - score_news(conn, target_date, api_key=None) がパブリック API。成功時は書込銘柄数（int）を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news 抽出、OpenAI（gpt-4o-mini, JSON mode）を用いた macro_sentiment 評価、重み付け合成、クリップ処理を実装。
    - API 呼び出しのリトライ/バックオフ、API 失敗時の macro_sentiment = 0.0 のフェイルセーフ。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。失敗時は ROLLBACK を試みて例外を伝播。
    - テスト用フック: _call_openai_api を patch 可能。
    - score_regime(conn, target_date, api_key=None) がパブリック API。成功時は 1 を返す。

- データ関連（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義し取得数・保存数・品質問題・エラーの集約を行う。
    - 差分更新ロジックの基礎（最終取得日判定、backfill_days による再取得）や DuckDB テーブル存在チェック等のユーティリティを実装。
    - 市場カレンダー補助（_get_max_date 等）を提供。
    - jquants_client と quality モジュール経由でのデータ取得・品質チェックを想定。
  - calendar_management モジュール
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB にデータがある場合は DB 値優先、未登録日や NULL は曜日ベースでフォールバック（週末は非営業日扱い）。
    - calendar_update_job による J-Quants からの差分取得、バックフィル（直近 _BACKFILL_DAYS 再取得）、健全性チェック（将来日が過剰な場合はスキップ）を実装。
    - JPX カレンダーの夜間更新ジョブの骨格を提供（jquants_client を介して fetch / save を呼ぶ）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、ma200_dev、ボラティリティ（20日 ATR, ATR pct）、流動性（20日平均売買代金、出来高比）等の計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)（raw_financials から EPS/ROE を取得して PER/ROE を算出）
    - DuckDB SQL を多用し、価格・財務データのみ参照。結果は (date, code) をキーとする dict のリストで返却。
    - データ不足時（必要行数未満）は None を返す設計。
  - feature_exploration
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)
      - デフォルト horizons=[1,5,21]、horizons の検証（正の整数かつ <= 252）
      - リード/ラグによる効率的な単一クエリ実装
    - IC 計算（スピアマンの順位相関）: calc_ic(factor_records, forward_records, factor_col, return_col)
      - None 値除外、十分なサンプル（>=3）でない場合は None を返す
    - rank(values) と factor_summary(records, columns) によりランク化・統計サマリーを提供
    - pandas 等外部依存を使わず純粋 Python + DuckDB で実装

- その他の実装上の注意点（ドキュメント化された設計方針）
  - ルックアヘッドバイアス防止のため、どの AI/スコア算出処理も内部で datetime.today() / date.today() を直接参照しない（target_date を明示的に渡す設計）。
  - OpenAI 呼び出しでの JSON モード利用とレスポンス頑健化（前後余計なテキストが混入した場合の {} 抽出復元処理）。
  - DuckDB のバージョン差異を考慮した実装（executemany 空配列回避、リストバインドの互換性回避など）。
  - ロギングによる挙動可視化（INFO/DEBUG/WARNING を活用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の秘匿情報は環境変数経由で扱う設計（Settings で必須チェック）。
- .env 自動読み込みは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Known limitations / 注意事項
- OpenAI クライアントは gpt-4o-mini を想定しているため、将来的なモデル変更でプロンプト/レスポンス処理の調整が必要になる可能性あり。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持つ（モジュール間でのプライベート関数共有をしない設計）。テスト時には各モジュールで patch する必要あり。
- time zone の扱い:
  - calc_news_window は JST ベースでウィンドウを定義し、戻り値は UTC naive datetime（DB の raw_news.datetime は UTC 保存を想定）。
- DuckDB への書き込みは冪等性を重視しているが、部分的障害時の振る舞い（部分成功の取り扱い）は各処理で説明があるので注意。
- エラー耐性: API 失敗やパース失敗時は基本的に例外を上位へ投げず（フェイルセーフ）、ログ出力して 0 や空辞書等でフォールバックする実装箇所がある。致命的な DB 書き込み失敗時は例外を伝播。

----

今後の予定（想定）
- テストカバレッジの充実（各モジュールのユニットテスト、OpenAI API のモック検証）。
- データ品質チェック（quality モジュール）の拡充と ETL の統合テスト強化。
- モデル／プロンプト最適化や運用向け監視（モニタリング・アラート）機能の追加。

If you want, releaseノートを英語版で追加したり、より詳細なモジュール別の変更点（関数一覧・引数の例・戻り値の型）を追記します。どの形式がよいか指示してください。