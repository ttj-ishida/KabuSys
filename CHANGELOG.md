CHANGELOG
=========

すべての表記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

[Unreleased]
------------

- （現時点の開発ブランチ用。リリース準備中の変更がある場合にここへ記載します。）

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ初期リリースを追加。バージョン: 0.1.0
- コアパッケージ構成
  - kabusys パッケージのエントリポイントを追加（__all__ に data/strategy/execution/monitoring を公開）。
- 設定管理 (kabusys.config)
  - .env ファイルと環境変数からの設定読み込みを実装。
  - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - export 付き行、クォート付き値、インラインコメント等を考慮した堅牢な .env パーサーを実装。
  - 必須環境変数取得用の _require、各種設定プロパティ（J-Quants、kabu API、Slack、DBパス、監視閾値、環境モード、ログレベルなど）を提供。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄ごとのテキストを OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチサイズ、記事数・文字数トリム、JSON Mode のレスポンス検証・パース、スコアの ±1.0 クリップを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ、API 失敗時のフェイルセーフ（スキップ継続）。
    - ai_scores テーブルへの冪等的な書き込み（該当コードの DELETE → INSERT）を実装。
    - calc_news_window: JST を基準にニュース収集ウィンドウの計算ロジックを実装（前日15:00～当日08:30 JST に対応）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（225連動ETF）の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成し、日次でレジーム (bull/neutral/bear) を判定。
    - prices_daily からの MA 計算、raw_news からキーワードフィルタしたマクロ記事取得、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを実装。
    - API 呼び出しのリトライ、5xx/ネットワークエラーの扱い、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - 実行において内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
  - AI モジュール全体で OpenAI クライアント呼び出しをラップし、ユニットテスト向けに差し替え可能な実装。

- データモジュール (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを元に営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 未取得時の曜日ベースフォールバック、DB の部分的な欠損（NULL）への警告と一貫した補完ロジックを提供。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新する夜間バッチ処理を実装（バックフィル・健全性チェックあり）。
  - ETL パイプライン (pipeline.ETLResult / etl)
    - ETL 実行結果を格納する ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供）。
    - 差分取得、バックフィル、品質チェック、idempotent 保存を想定した基盤設計（jquants_client・quality 連携）。
  - jquants_client のインターフェースを利用する形での ETL ワークフロー設計（実データ取得・保存関数は外部モジュールと連携）。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: mom_1m/3m/6m、および 200 日 MA 乖離の算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出（データ不足時は None）。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を算出（EPS 不在時は None）。
    - DuckDB を利用した SQL ベースの高速計算実装、外部API呼び出しなしの安全設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。必要なレコード数が不足する場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（float の丸めを行い ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算するユーティリティ。
    - pandas 等外部依存を避けた標準ライブラリ実装。

- 共通実装・設計上の配慮
  - DuckDB を主要ストレージとして利用する想定（DuckDB 接続を各関数に注入）。
  - ルックアヘッドバイアス防止のため、日付計算や DB クエリにおいて未来データ参照を避ける設計。
  - API 呼び出し（OpenAI / J-Quants）に関してはリトライとフェイルセーフを組み込み、部分失敗時のデータ保護（部分的な DELETE → INSERT）を考慮。
  - ロギングを各モジュールで利用し、警告・情報・例外ログを適切に出力。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 既知の制限
- OpenAI / J-Quants など外部 API の利用は API キーやネットワーク環境に依存するため、実行環境での設定が必要（環境変数 OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN など）。
- 本リリースでは一部の名前空間（strategy, execution, monitoring）の実装はパッケージ公開対象として存在するが、今回提示されたソース内に全機能の実装が揃っていない可能性があります（実装の続きは今後のリリースで追加予定）。
- DuckDB のバインド挙動（executemany に空リスト不可など）に合わせた回避処理を実装しているため、使用する DuckDB バージョンとの互換性に留意してください。

Acknowledgments
- 本プロジェクトは、DuckDB と OpenAI の Chat Completions（JSON mode）を主要技術として利用しています。