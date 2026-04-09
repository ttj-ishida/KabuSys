Keep a Changelog
=================

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog の形式に準拠します。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

初回公開リリース。日本株自動売買プラットフォーム "KabuSys" のコア機能群を実装しました。
主にデータ取得・ETL・カレンダー管理・ファクター計算・ニュースNLP および市場レジーム判定を提供します。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ (バージョン 0.1.0)。公開サブパッケージとして data, research, ai, execution, monitoring, strategy, etc. を想定したエクスポート定義を追加。
- 設定・環境変数管理
  - kabusys.config
    - .env / .env.local ファイルをプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export KEY=val 形式、クォート／エスケープ、行内コメントなどを考慮した .env パーサー実装。
    - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、LINE トークン、DB パス、Paper Trading 設定、監視閾値、実行環境・ログレベル判定など）。
    - 環境変数のバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）は ValueError を発生させることで不正設定を早期検出。
- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp.score_news
    - raw_news / news_symbols を集約し、銘柄ごとにニュース本文を結合して OpenAI (gpt-4o-mini) に JSON Mode でバッチ送信してセンチメントスコアを ai_scores テーブルへ書き込む。
    - トークン肥大化対策（1銘柄あたり最大記事数・最大文字数）、バッチサイズ制御（最大 20 銘柄/コール）、レスポンスの厳密バリデーション、スコアを ±1.0 にクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライと、失敗時のフェイルセーフ（該当チャンクのスキップ）を実装。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照せず、target_date 指定でウィンドウを計算。
  - kabusys.ai.regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、ニュースNLP ベースのマクロセンチメント（重み 30%）を合成し市場レジーム（bull/neutral/bear）を daily 単位で判定して market_regime テーブルへ冪等書き込み。
    - マクロニュース取得（キーワードフィルタ）、OpenAI 呼び出し（gpt-4o-mini）による JSON レスポンスパース、API エラー時のフォールバック macro_sentiment=0.0。
    - レジーム合成ロジック、閾値定義、冪等な DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - 共通設計
    - OpenAI 呼び出しはテストしやすく private 関数に分離（モック可能）。
    - API失敗時のロギングと安全なフォールバック動作を重視。
- データプラットフォーム（Data）
  - kabusys.data.calendar_management
    - market_calendar テーブルベースの営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に calendar データがない場合は曜日ベース（土日非営業）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等で更新（バックフィル・健全性チェック含む）。
  - kabusys.data.pipeline / ETL
    - ETLResult データクラス（pipeline.ETLResult）を実装し kabusys.data.etl で公開。
    - ETL の設計方針を反映した差分取得、backfill、品質チェック（quality モジュールとの連携を想定）を定義（実行ロジックは pipeline 内で表現）。
    - ETL 実行結果に品質問題を収集して上位へ伝搬できる構造を提供。
- リサーチ・ファクター計算
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を参照）。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER・ROE を計算（EPS が 0 または欠損の場合は None）。
    - 全関数は DuckDB SQL を活用し、外部 API にはアクセスしない設計。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得するクエリ実装（LEAD を利用）。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。十分な有効データがない場合は None を返す。
    - rank / factor_summary: 同順位処理を考慮したランク化と基本統計量サマリー機能を実装。
- ロギング・デバッグサポート
  - 各モジュールで詳細な logger 呼び出しを配置し、失敗時の警告/情報ログにより運用時の原因追跡を容易に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動読み込み時に OS 環境変数を保護（.env の上書き制御）。KABUSYS_DISABLE_AUTO_ENV_LOAD により意図せぬ環境ロードを回避可能。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアスの排除: AI バッチ処理およびファクター計算はすべて target_date を明示しており、datetime.today()/date.today() に依存しない設計。
- DB 操作は冪等性を意識: market_regime や ai_scores などは既存レコードの削除→挿入で置換する処理を採用し、部分失敗が他データに影響しないよう配慮。
- DuckDB 互換性: executemany の空リスト制約など DuckDB の実装差異への対応ロジックを組み込んでいる。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）失敗時は例外で全面停止させず、可能な限り局所的にフォールバック（スコア 0.0、チャンクスキップ 等）して処理を続行する方針。

Authors
- KabuSys 開発チーム（実装から推測）

Acknowledgments
- DuckDB を用いたローカル分析パイプライン、OpenAI JSON Mode を利用したニューススコアリング設計に基づく実装。

-- end of changelog --