Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは[Keep a Changelog](https://keepachangelog.com/ja/1.0.0/)規約に準拠します。  
バージョン番号は semver に従います。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開モジュール一覧を __all__ に定義。
- 環境設定 / ロード機能（kabusys.config）を追加。
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - export KEY=val 形式、クォート／エスケープ、インラインコメントの扱いに対応した .env パーサ実装。
  - 必須環境変数チェック用の _require と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の検証と is_live/is_paper/is_dev のユーティリティを持つ。
- AI 関連機能（kabusys.ai）を追加。
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - チャンク処理（1チャンク最大 20 銘柄）、1銘柄あたり記事数/文字数上限（記事数:10、文字数:3000）を実装。
    - JSON Mode を期待しつつ前後余分テキストが混ざる場合の復元ロジック、レスポンスバリデーション、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライを実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - DuckDB への書き込みは部分失敗で既存スコアを消さない設計（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う機能を実装。
    - prices_daily と raw_news を参照し、DuckDB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ挙動。
    - OpenAI 呼び出しでのエラー分類（RateLimit/APIConnection/APITimeout/APIError）とリトライロジックを実装。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを用いる設計。
- データプラットフォーム関連（kabusys.data）を追加。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日 / SQ 日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーデータがない場合は曜日ベース（週末除外）でフォールバックする一貫した設計。
    - 夜間バッチ更新 job（calendar_update_job）：J-Quants API から差分取得し冪等保存（バックフィル、健全性チェックを含む）。
    - 最大探索日数やバックフィル日数、先読み日数等の設定とサニティチェックを実装。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（ETL 実行の取得数・保存数・品質問題情報・エラー等を集約）。
    - 差分取得・保存・品質チェックのためのユーティリティ（_get_max_date, _table_exists など）。
    - デフォルトのバックフィル動作とエラー/品質問題の扱い（Fail-Fast ではなく呼び出し元で判断）を実装。
  - jquants_client のラッパ（jq）を想定した差分保存処理との連携設計。
- リサーチ機能（kabusys.research）を追加。
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の SQL と Python で計算する関数を提供。
    - データ不足時の None 扱いやスキャンレンジのバッファ設計（ルックバック日数の確保）を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク化ユーティリティ、統計サマリーを実装。
    - rank 関数は同順位を平均ランクで処理し、浮動小数丸めによる ties を round(v, 12) で安定化。
    - calc_ic は有効データが 3 件未満の場合に None を返す安全設計。
- その他の実装・公開
  - ai/__init__.py、research/__init__.py、data/etl.py などで公共 API を適切に再エクスポート。

Changed
- （初回リリースのため特記なし）

Fixed
- DuckDB の executemany に空リストを渡せない問題を回避するチェックを追加（score_news の書き込み処理）。
- OpenAI レスポンスの JSON 解析で前後余分テキストが混ざるケースに対する復元ロジックを追加（news_nlp._validate_and_extract / regime_detector の JSON パース回避処理）。
- DB 書き込み失敗時に ROLLBACK を試行し、失敗した場合は警告ログを出す（regime_detector / news_nlp / pipeline のトランザクション処理）。

Security
- （公開 API キーやシークレットは環境変数経由で取得する設計。初期リリースにおける既知のセキュリティ修正はなし）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止: ほとんどの日時計算は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時はスコアやセンチメントを中立値にフォールバックするなど、ワークフローを停止させない挙動を優先。
- DuckDB を主要なデータストアとして想定。SQL と Python を組み合わせて演算を行う設計。
- テストしやすさ: OpenAI 呼び出し箇所は差し替え可能に設計（関数を patch してモック可能）。

Acknowledgements
- 本リリースは内部仕様ドキュメント（StrategyModel.md / DataPlatform.md 等）に基づく実装を含みます。