CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

注記
----
リリース日やバージョン番号はコードベースのメタ情報（__version__）および実行時日付を基に推測して記載しています。実装上の設計方針やログメッセージ、エラーハンドリングから想定される挙動を元に特徴・制約も併記しています。

Unreleased
----------
- （現在のところ未リリースの変更はありません）

0.1.0 - 2026-03-29
------------------

Added
- パッケージの初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサは以下をサポート：
    - コメント行、空行、"export KEY=..." 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無し行のインラインコメント判定（直前が空白/タブの場合）
  - OS 環境変数を保護するための protected キーセットを利用した上書き制御（.env.local は override=True だが OS 環境変数は上書きしない）。
  - Settings クラスで主要設定値をプロパティとして提供（OpenAI / J-Quants / kabu ステーション / Slack / DB パス等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証と便利プロパティ（is_live, is_paper, is_dev）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - ニュース記事の時間ウィンドウ計算（calc_news_window）。
    - raw_news / news_symbols から銘柄別に記事集約（最大記事数・文字数トリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄／チャンク）、JSON モードレスポンスの検証とスコア抽出。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をモックできる設計。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）の直近200日MA乖離（重み70%）とマクロニュースLLMセンチメント（重み30%）を合成して市場レジーム判定（bull/neutral/bear）。
    - マクロニュース抽出にマクロキーワードリストを使用、最大記事数を制限。
    - OpenAI API 呼び出し（gpt-4o-mini）で macro_sentiment を取得、失敗時はフェイルセーフで 0.0 を採用。
    - レジームのスコア計算と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）およびロールバック処理の保護。
    - テスト向けに _call_openai_api を差し替え可能。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPXカレンダーの夜間バッチ更新ジョブ（calendar_update_job）：J-Quants API から差分取得 -> market_calendar へ保存（バックフィル・健全性チェックあり）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - DB 登録が無い場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループを防止。
  - pipeline:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプラインのユーティリティ（差分取得、バックフィル、品質チェックとの統合、id_token 注入可能設計の方針）。
    - DB テーブル存在チェック、テーブル最大日付取得ユーティリティを実装。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を計算（複数ホライズンをまとめて1クエリで取得）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効レコードが3未満で None）。
    - rank: 同順位は平均ランクにする関数（丸めで ties を検出）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- パッケージ初期エクスポート
  - kabusys.__all__ の設定（data, strategy, execution, monitoring）。
  - 主要ユーティリティや関数の __all__ 再エクスポート（例: kabusys.data.ETLResult、kabusys.ai.score_news 等）。

Reliability / Safety
- ルックアヘッドバイアス対策:
  - datetime.today() / date.today() を多くのスコア計算で直接参照せず、target_date ベースで計算を行うよう設計。
  - DB クエリに date < target_date や排他条件を使い将来データを参照しない工夫。
- OpenAI 呼び出しのフォールバック:
  - レート制限・ネットワーク障害・サーバー5xx等を検出してリトライまたは 0.0 / スキップ として処理継続。
  - API エラー時に例外を投げずに安全なデフォルトを返す箇所があり、バッチ全体の失敗を防止。
- DB トランザクションの安全化:
  - 書き込み処理は BEGIN / COMMIT を使用し、例外時は ROLLBACK を呼ぶ（ROLLBACK 自体の失敗は警告ログ）。

Testing / Developer friendliness
- OpenAI 呼び出し点（_kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）をユニットテストでパッチ可能に設計。
- 環境変数自動読み込みを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テスト環境での副作用を軽減。

Fixed
- 初期リリースのためなし（実装時に想定された一般的な問題点へ対処済みの旨を反映）。

Changed
- 初期リリースのためなし。

Removed
- 初期リリースのためなし。

Notes / 既知の制約
- 外部依存:
  - DuckDB と J-Quants API、OpenAI（gpt-4o-mini）、および kabuステーション API（kabuapi）との連携を前提とする。
  - Slack 連携のための SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を Settings で必須にしている。
- OpenAI の API キーは api_key 引数または環境変数 OPENAI_API_KEY に設定する必要があり、未設定時は ValueError を送出する関数がある（score_news, score_regime）。
- 日付/時間:
  - news のウィンドウ計算は JST を基準にして UTC naive datetime を返す。呼び出し側は raw_news.datetime が UTC で保存されている前提で使用する必要がある。
- 不完全な箇所:
  - pipeline._adjust_to_trading_day がファイル途中で終わっているように見える（コード断片で終了）ため、将来的に補完が必要な可能性あり。
- 出力値／戻り値:
  - score_regime は成功時に 1 を返す設計。score_news は書き込んだ銘柄数を返す。
- 挙動:
  - データ不足時には多数の関数が None や中立値（例: ma200_ratio=1.0、macro_sentiment=0.0）を返す仕様になっているため、呼び出し側でこれらを扱う必要がある。

Migration / Upgrade notes
- 初回公開バージョンのため旧バージョンからの互換性対応は不要。
- 今後のバージョンで API（関数シグネチャ）や DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar 等）に変更が入ると後方互換性に影響する可能性あり。データベーススキーマの変更は注意して行うこと。

Contributors
- この CHANGELOG はコード内容からの推測に基づいて生成されています。実際の貢献者やコントリビューション履歴はリポジトリのコミットログを参照してください。

--- 
（以上）