# CHANGELOG

全ての注目すべき変更はこのファイルに記載します。  
このプロジェクトは "Keep a Changelog" に準拠しています。  

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- 初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加。
  - パッケージ公開情報
    - kabusys.__version__ = "0.1.0"
    - パブリック API: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定をロードする自動読み込み機能を実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - 自動ロードを無効にするための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装:
    - export KEY=val 形式サポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント処理（クォート外で "#" の前に空白がある場合をコメントと判定）
  - ファイル読み込み失敗時は警告を出力してフォールバック
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを環境変数から取得
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値セットを持つ）
    - is_live / is_paper / is_dev の便利プロパティ
    - 必須値未設定時は ValueError を送出する _require を利用

- AI 関連 (kabusys.ai)
  - news_nlp:
    - raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score（センチメント）を ai_scores テーブルへ書き込み
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を実装
    - gpt-4o-mini の JSON mode を利用し、出力のバリデーションを厳密に行う
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 再試行・バックオフ: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ
    - レスポンスの厳格な検証（results 配列、code の存在、スコア数値化、±1.0 でクリップ）
    - 書き込みはトランザクションで行い、部分失敗時に他コードの既存スコアを保護（DELETE → INSERT、DuckDB executemany の空リスト対策あり）
    - テスト容易性: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch）

  - regime_detector:
    - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定
    - マクロニュースは news_nlp の calc_news_window を再利用して期間を決定し、raw_news からマクロキーワードでフィルタしたタイトルを LLM に投げる
    - OpenAI 呼び出しは内部で再試行を行い、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用
    - レジームスコアの合成と閾値判定（BULL/BEAR threshold）を実施し、market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト容易性: news_nlp と内部関数を共有せず、_call_openai_api の差し替えでテスト可能

- Data / ETL (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル）と営業日ロジックを提供
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを実装
    - market_calendar 未取得時は曜日ベース（土日除外）でフォールバックする設計
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新するジョブを実装
      - バックフィル（直近 _BACKFILL_DAYS を再フェッチ）
      - 健全性チェック（last_date が極端に未来の場合はスキップ）
      - API 失敗や保存失敗時は例外を捕捉して 0 を返す
  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）
      - ETL 実行の取得/保存件数、品質問題、発生エラーなどを集約
      - has_errors / has_quality_errors / to_dict を提供
    - ETL パイプライン補助関数:
      - 差分取得のための最終日取得、バックフィル、品質チェックの設計方針を実装
      - DuckDB 上で安全に最大日付を取得するユーティリティ等を実装

- Research（kabusys.research）
  - factor_research:
    - Momentum, Value, Volatility, Liquidity 等の定量ファクター計算関数を追加
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（窓内不足時は None）
      - calc_value: per, roe（raw_financials から最新財務データを取得して計算）
    - DuckDB の SQL とウィンドウ関数を活用した実装で外部 API にはアクセスしない設計
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。利用可能レコードが少ない場合は None を返す
    - rank: 同順位は平均ランクを与えるランク付けユーティリティ（丸めによる ties の扱いを考慮）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能（None 値除外）
  - 研究ユーティリティは標準ライブラリのみで実装され、pandas など外部依存を持たない

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: 多くの関数で datetime.today() / date.today() を直接参照せず、target_date を引数で受ける設計を採用
- 機外API呼び出しの堅牢性: OpenAI 呼び出しはリトライ戦略・フェイルセーフ（デフォルトの代替値）・レスポンス検証を備える
- DuckDB 互換性: executemany の空リスト問題や日付型の取り扱いに配慮した実装
- テスト容易性: OpenAI 呼び出しや内部 I/O を差し替え可能にしてユニットテストが容易になるよう配慮

---

今後のリリースでは、strategy / execution / monitoring の実装の詳細化、より豊富なメトリクスとモニタリング、発注ロジックの実装、さらなるテストカバレッジ向上を予定しています。