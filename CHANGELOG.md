保持すべき変更履歴 (Keep a Changelog 準拠)
全ての目立つ変更を記録します。セマンティック バージョニングを使用します。

[Unreleased]
- （現在未リリースの変更はありません）

[0.1.0] - 2026-03-27
Added
- パッケージ初版リリース。
- 基本構成
  - kabusys パッケージの公開バージョンを 0.1.0 として追加。
  - __all__ に data, strategy, execution, monitoring をエクスポート。
- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードの探索はパッケージファイル位置からプロジェクトルート（.git または pyproject.toml）を特定して行うため、CWD に依存しない挙動。
  - .env パース強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート中のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートあり/なしでの差別化）。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない（protected 機構）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須項目をプロパティで取得（未設定時は ValueError）。
  - 環境変数値検証: KABUSYS_ENV（development / paper_trading / live のみ）、LOG_LEVEL（DEBUG/INFO/...）のバリデーション。
  - DB パス設定: DUCKDB_PATH / SQLITE_PATH のデフォルトと expanduser 対応。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。
    - バッチ処理: 1 API コールあたり最大 20 銘柄、1銘柄最大 10 記事・3000 文字にトリム。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンス検証: JSON パース、"results" 構造、既知コードのみ採用、スコアは ±1.0 にクリップ。
    - 書き込みは部分失敗を避けるため、スコア取得済みコードのみを DELETE → INSERT で置換（トランザクション処理、DuckDB executemany 空リスト対応に注意）。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ保存。
    - マクロニュース抽出はキーワードベース（日本／米国・グローバルのキーワード群サポート）。
    - LLM 呼び出しは gpt-4o-mini、JSON 出力を期待し、API エラー時は macro_sentiment=0.0 でフェイルセーフ。
    - リトライ（RateLimit/APIConnection/APITimeout/5xx）を実装。API レスポンスのパース失敗や例外は警告ログに落とす設計。
    - DB 書き込みは冪等性を保つため BEGIN / DELETE / INSERT / COMMIT のパターンを採用し、エラー時は ROLLBACK を試行。
- データ処理・研究モジュール
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを用意し、取得件数・保存件数・品質問題・エラー概要を一元管理。
    - 差分取得のためのヘルパー（テーブルの最大日付取得など）を実装。
    - カレンダー先読み・バックフィル・品質チェック方針を記載。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間バッチ更新 calendar_update_job を実装（J-Quants から差分取得 → 保存）。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが欠けている場合は曜日日ベースでフォールバック（週末を非営業日扱い）。DB 登録優先の一貫したロジック。
    - 最大探索期間を設定して無限ループ防止、バックフィル期間や健全性チェックを実装。
  - リサーチ（kabusys.research）
    - factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算関数を実装（prices_daily / raw_financials を参照）。
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率など。
      - calc_value: PER（EPS が無効時は None）と ROE（最新の raw_financials を参照）。
    - feature_exploration: 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）、IC 計算（スピアマンのランク相関）、統計サマリー（count/mean/std/min/max/median）、ランク変換ユーティリティ。
    - 設計方針: DuckDB を用いた純粋な SQL / 標準ライブラリ実装。外部 API や取引実行機能には依存しない。
- データモジュール公開
  - kabusys.data.etl が ETLResult を再エクスポート。

Changed
- （初版のため履歴なし）

Fixed
- （初版のため履歴なし）

Security
- すべての外部 API キーは環境変数で管理（コードにベタ書きなし）。OpenAI キー未設定時は明示的に ValueError を発生させることで誤った実行を回避。
- .env 読み込みは OS の既存環境変数を上書きしない（protected set）ため、CI/OS レベルの値を保護。

Notes / Implementation details
- 多くのモジュールで「ルックアヘッドバイアス防止」の設計方針を採用：datetime.today()/date.today() を参照しないようにして、呼び出し側から target_date を明示的に渡す設計。
- DuckDB の互換性考慮（executemany に空リスト不可など）をコード内に明記・対応。
- OpenAI 呼び出しは JSON mode を利用し、応答の堅牢なパースと検証を行うことで LLM 出力の不確実性に耐性を持たせている。
- テスト容易性のため、OpenAI 呼び出しを差し替え可能（patch 可能）に実装。
- トランザクション処理（BEGIN/COMMIT/ROLLBACK）で DB 操作の一貫性を担保。ROLLBACK に失敗した場合は警告ログ。

参照
- セマンティックバージョニング: https://semver.org/
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/