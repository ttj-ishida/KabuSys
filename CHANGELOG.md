# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを公開します。主にデータ取得・ETL、カレンダー管理、リサーチ（ファクター計算）、AI を使ったニュース解析・市場レジーム判定、設定管理のユーティリティを含みます。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開モジュール: data, strategy, execution, monitoring。
  - パッケージバージョンを `0.1.0` として定義。

- 設定管理
  - 環境変数／.env ファイル読み込みモジュールを実装（kabusys.config）。
  - プロジェクトルート探索（.git または pyproject.toml 基準）により、カレントワーキングディレクトリに依存せず .env を自動読み込み。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能（テスト用途）。
  - .env パーサにて export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境フラグ等のプロパティを提供）。環境変数チェックとバリデーションを実装。

- AI（自然言語処理／市場判定）
  - kabusys.ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、各銘柄のセンチメント（ai_score）を ai_scores テーブルへ書き込む機能を実装。
    - ニュース収集ウィンドウ計算（JST基準、UTC変換）を提供。
    - 1銘柄あたりの最大記事数・文字数トリム、チャンク化（20銘柄）を実装。
    - JSON Mode を利用しレスポンスを厳密にバリデート。部分失敗時の DB 置換ロジック（DELETE → INSERT）により冪等性を確保。
    - レート制限 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフリトライを実装。
    - テスト用に OpenAI 呼び出し関数をパッチ可能（unittest.mock.patch 対応）。
  - kabusys.ai.regime_detector: ETF（1321）の200日移動平均乖離とマクロニュース（LLMセンチメント）を組み合わせ、'bull' / 'neutral' / 'bear' の市場レジームを日次判定して market_regime テーブルへ冪等書き込みする機能を実装。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータを使用）。
    - マクロキーワードによるニュース抽出、LLM によるマクロセンチメント評価、重み付け合成。
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）やリトライ処理。
    - OpenAI クライアント呼び出しはニュースモジュールと独立した実装でモジュール結合を低減。

- データ（Data Platform）
  - kabusys.data.pipeline / ETLResult: ETL 実行のためのユーティリティと結果データクラスを提供（取得数・保存数・品質問題・エラーの集約）。
  - kabusys.data.calendar_management:
    - market_calendar を用いた市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等）。
    - calendar_update_job 実装（J-Quants から差分取得して冪等に保存、バックフィル・健全性チェックあり）。
    - DB 登録がない場合の曜日ベースフォールバックをサポート（カレンダーがまばらな場合でも一貫性を保持）。

- リサーチ（Research）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: PER、ROE を raw_financials と prices_daily から計算。
    - DuckDB を使った SQL+Python ハイブリッド実装で高効率に算出。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算を追加（horizons のバリデーションあり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算実装。
    - rank: 同順位は平均ランクにするランク変換ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装。
  - zscore_normalize をデータユーティリティから再エクスポート。

### Changed
- （初回リリース）設計ガイドライン・実装上の注意点を文書化（各モジュールの docstring に明記）。
  - ルックアヘッドバイアス防止のため date.today()/datetime.today() を内部処理で参照しない方針を採用。
  - DuckDB 互換性・実行時の空パラメータ問題（executemany 空リスト不可）への対策を実装。

### Fixed
- N/A（初回リリースのため既知のバグ修正履歴なし）

### Security
- API キーや機密情報の取り扱い:
  - Settings にて必須の環境変数チェックを導入（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - .env 自動ロード時に既存 OS 環境変数を保護（protected set）する仕組みを実装。

### Notes / Usage
- OpenAI API を使用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数 api_key によりキーを供給する必要があります。未設定時は ValueError を送出します。
- DuckDB を内部 DB として想定。各種テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提です。
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 謝辞
このリリースはデータプラットフォーム・研究・AI モジュールを一体化した初期実装です。今後、監視・実行（注文連携）や追加の品質チェック、ドキュメント強化、テストカバレッジ拡充を予定しています。