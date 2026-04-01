CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

履歴
----

### Unreleased
- 今後のリリースでの変更をここに記載します。

### [0.1.0] - 2026-04-01
初回リリース（ベース実装）。以下の主要機能と設計方針を追加しました。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）と公開モジュール定義。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - export 形式・コメント・クォート・エスケープを考慮した .env 行パーサを実装。
  - 必須環境変数チェック（_require）と各種設定プロパティ（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境モード・ログレベル等）。
  - 環境値検証（KABUSYS_ENV、LOG_LEVEL の許容値チェック）を実装。
- AI 関連（kabusys.ai）
  - news_nlp モジュール: ニュース記事のまとめスコアリング機能を実装（score_news）。
    - OpenAI（gpt-4o-mini）を用いた JSON Mode の呼び出し、レスポンス検証、スコアの ±1.0 クリップ、バッチ処理（最大 20 銘柄/チャンク）。
    - タイムウィンドウ計算（JST 指定 → UTC 変換）と銘柄ごとの記事結合・トリム処理。
    - 再試行（429/ネットワーク/タイムアウト/5xx）向けエクスポネンシャルバックオフ。
    - テスト用に _call_openai_api を差し替え可能に設計。
    - ai_scores テーブルへの冪等的な書き込み（DELETE → INSERT）を実装。部分失敗時に既存スコアを保護する設計。
  - regime_detector モジュール: 市場レジーム判定（score_regime）を実装。
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジームを判定（bull / neutral / bear）。
    - DuckDB からの過去データ参照でルックアヘッドバイアスを防止（target_date 未満を使用）。
    - LLM 呼び出しの再試行・フェイルセーフ（失敗時 macro_sentiment = 0）処理。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
- データ基盤（kabusys.data）
  - calendar_management モジュール:
    - JPX マーケットカレンダーの取得・夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定・前後営業日検索・期間内営業日取得・SQ日判定機能（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日の曜日フォールバック、および最大探索日数制限などの堅牢性設計。
  - pipeline / ETL:
    - ETL の結果を表す ETLResult データクラスの導入（取得件数、保存件数、品質問題、エラー概要など）。
    - 差分更新・バックフィル・品質チェックを想定した ETL 設計（デフォルト backfill 等の定数を含む）。
    - データ取得・保存のための jquants_client 経由の処理設計を想定。
  - ETLResult を外部に公開するための etl モジュール再エクスポート。
- Research（kabusys.research）
  - ファクター計算（factor_research）:
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損なら None）、ROE（raw_financials からの取得）。
    - DuckDB を用いた SQL ベース実装。データ不足時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（スピアマンのランク相関 calc_ic）。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）。
  - 研究向けユーティリティをまとめて __all__ で公開。
- 共通設計上の注意 / フェイルセーフ
  - すべてのモジュールでルックアヘッドバイアスを避けるため date.today()/datetime.today() を内部ロジックで直接参照しない設計を採用（target_date を外部注入）。
  - OpenAI API 呼び出しはモジュール毎に private wrapper を用意し、テスト時に差し替え可能にして結合を緩める。
  - API 呼び出しに対しては再試行（指数バックオフ）や 5xx の扱い、パース失敗時のフェイルセーフ（ゼロやスキップ）などの堅牢化処理を実装。
  - DuckDB に対する executemany の空パラメータ問題への対処（params が空であれば実行しないガード）。
  - ロギングを多用し処理状況・警告・例外を記録。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キーやトークンは環境変数で管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。必須チェックを実装。

Notes / 既知の設計制約
- DuckDB を主な永続化ストアとして想定しており、SQL 文で日付・ウィンドウを絞って計算する設計です。
- OpenAI のレスポンス信頼性に依存する部分があるため、API 呼び出し失敗時は明示的にフォールバック（0.0 やスキップ）します。運用時は API キーのレート制限やコストに注意してください。
- 一部の関数はテスト用に内部呼び出しを差し替え可能ですが、外部 API クライアント（jquants_client 等）の具象実装は別途提供する必要があります。

開発者向け補足
- 環境依存の自動読み込みをスキップするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストや CI で便利です）。
- OpenAI 呼び出しの差し替えは各モジュール内の _call_openai_api をモックすることで可能です（unittest.mock.patch 等）。

--- 

（注）この CHANGELOG は提供されたソースコードから機能・設計を推測して作成しています。実際のリリースノート作成時はリリース日・コミットハッシュ・外部依存（jquants_client 実装など）を追記してください。