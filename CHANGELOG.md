Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

CHANGELOG.md
=============
すべての重要な変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の原則に従っています。

Unreleased
----------
（今後の変更記録用）

0.1.0 - 2026-03-29
-----------------
初回リリース。以下の主要機能・実装を含みます。

Added
- パッケージ構成
  - パッケージ名: kabusys
  - 公開サブパッケージ: data, strategy, execution, monitoring（__init__.py でエクスポート）
- 設定管理
  - 環境変数・.env ファイル読み込み機能を実装（kabusys.config）
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）
  - .env と .env.local の読み込み優先度を実装（OS 環境変数 > .env.local > .env）
  - export KEY=val 形式やクォート・コメント処理に対応した .env パーサ実装
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスを公開（settings インスタンス経由で J-Quants/OpenAI/Slack/DB 等の設定にアクセス）
  - env（development/paper_trading/live）と LOG_LEVEL のバリデーションを追加
  - デフォルトの DB パス（duckdb/sqlite）の取得処理を提供
- AI モジュール
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを算出
    - タイムウィンドウ定義（前日15:00 JST ～ 当日08:30 JST に対応、UTC 変換済み）
    - バッチ処理（最大 20 銘柄 / バッチ）、記事数・文字数制限、レスポンス検証、スコア ±1.0 でクリップ
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフリトライ
    - レスポンスパース失敗や API エラー時はフェイルセーフでスキップ（例外を上げず継続）
    - スコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時の保護）
    - テスト用に _call_openai_api を差し替え可能な設計（unittest.mock.patch 利用想定）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - マクロキーワードによる記事抽出、OpenAI（gpt-4o-mini）でマクロセンチメントを算出
    - API エラーやレスポンスパース失敗時は macro_sentiment=0.0 にフォールバック
    - レジームスコア算出と regime_label ("bull"/"neutral"/"bear") 決定
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）およびロールバック処理
    - ルックアヘッドバイアス対策（date 比較は target_date 未満など厳密な排他条件を採用）
- Data モジュール
  - 市場カレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバック
    - 最大探索日数の制限や健全性チェック（未来日付の異常検出）を実装
    - calendar_update_job: J-Quants API から差分取得し冪等的に保存（バックフィル対応）
  - ETL パイプライン基盤（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（実行結果・品質問題・エラー情報等を集約）
    - データ差分取得、バックフィル、品質チェックの設計を反映
    - DuckDB の互換性に配慮したテーブル存在確認や最大日付取得ユーティリティを実装
    - jquants_client（外部）を使った取得・保存処理を想定
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m/3m/6m, ma200_dev（200日 MA に対する乖離）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
    - calc_value: per, roe（raw_financials と prices_daily を組合せ）
    - 全関数は DuckDB の prices_daily/raw_financials のみ参照、外部発注や API 呼び出しは行わない
    - データ不足時の None 返却、結果は (date, code) をキーにした dict リスト
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を使用）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算、データ不足時は None
    - rank: 平均ランクを計算（同順位は平均ランク）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
    - pandas 等に依存しない純 Python 実装（DuckDB + 標準ライブラリ）
- 汎用的な堅牢性・設計上の配慮
  - ルックアヘッドバイアスを避ける実装方針を全 AI/分析モジュールで徹底
  - OpenAI 呼び出しに対するリトライ・バックオフ・エラー処理を一貫して実装
  - DuckDB のバージョン差分（executemany の空リスト等）を回避するためのワークアラウンドを追加
  - トランザクション（BEGIN/COMMIT/ROLLBACK）と冪等性を重視した DB 書き込み
  - ロギング（logger）を広範に使用し、障害時には詳細をログ出力する

Changed
- 初版のため該当なし（初回リリース）。

Fixed
- 初版のため該当なし（初回リリース）。

Notes / 注意事項
- OpenAI API キーは api_key 引数（関数呼び出し時）または環境変数 OPENAI_API_KEY を使用する。
  未設定時は ValueError を発生させる箇所があるため、実行前に環境変数の設定が必要です。
- news_nlp / regime_detector は gpt-4o-mini の JSON mode を利用する設計だが、
  実際の API 仕様・レスポンスフォーマットに応じた動作確認が必要です。
- DuckDB を使用するため、実行環境に duckdb パッケージがインストールされている必要があります。
- J-Quants クライアント（kabusys.data.jquants_client）は外部依存を想定しており、
  実際の API 呼び出し・保存関数は別モジュールで提供される必要があります。
- research モジュールは本番口座や発注処理にアクセスしない設計で、リサーチ用途向けです。

今後の予定（ロードマップ・提案）
- strategy / execution / monitoring の実装拡充（現時点ではエクスポートのみ）
- テストカバレッジ拡大（API 呼び出しのモックや DB フィクスチャ）
- モデル/プロンプトのチューニングや OpenAI の別モデル対応
- J-Quants 周りのエラー処理・再試行ロジック強化

----- 
（この CHANGELOG はコードベースの構造・コメント・定数・関数シグネチャから推測して作成しています。実際のリリースノート作成時には変更差分・コミットログに基づく調整を行ってください。）