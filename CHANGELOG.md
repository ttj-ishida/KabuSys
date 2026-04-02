CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-02
--------------------

Added
- 初回リリース (0.1.0)
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パブリックモジュール: data, strategy, execution, monitoring を公開

  - 環境設定 / ロード (src/kabusys/config.py)
    - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - プロジェクトルートの自動探索: .git または pyproject.toml を起点に検索（CWD 非依存）
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応
    - .env パーサを実装
      - export KEY=val 形式に対応
      - シングル/ダブルクォートのエスケープ処理対応（バックスラッシュサポート）
      - コメント処理（クォート内無視、クォート外は '#' が直前に空白/タブのときコメントとみなす）
    - .env 上書きポリシーと保護キー機能（OS 環境変数を protected として上書き防止）
    - Settings クラスを実装し、主要設定値をプロパティで提供
      - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等
      - 必須キー未設定時は ValueError を送出する _require() を提供
      - is_live/is_paper/is_dev ヘルパーを提供
      - 値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）

  - AI モジュール（src/kabusys/ai）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を集約し、銘柄別にニュースを結合して OpenAI (gpt-4o-mini) に送信
      - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算機能（calc_news_window）
      - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたり記事数上限・文字数トリム実装
      - JSON Mode を用いたレスポンス処理と堅牢なバリデーション（results 配列検証、未知コード無視、数値チェック）
      - スコアを ±1.0 にクリップ
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフでのリトライ
      - DuckDB への書き込みは部分的置換（該当 code の DELETE → INSERT）で部分失敗時の保護を実装
      - executemany の空リストバグ（DuckDB 0.10 への配慮）を考慮したガード実装
      - public API: score_news(conn, target_date, api_key=None) -> 書き込み銘柄数
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して
        日次で市場レジーム（bull / neutral / bear）を判定
      - マクロセンチメントは raw_news からマクロキーワードで抽出したタイトル群を OpenAI（gpt-4o-mini）に渡して評価
      - LLM 呼び出しは JSON パース・リトライ（429/ネットワーク/タイムアウト/5xx を考慮）を実装
      - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
      - レジームスコア合成後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
      - public API: score_regime(conn, target_date, api_key=None) -> 1（成功）

    - ai パッケージ __all__ とエクスポートを設定（score_news を公開）

  - Data モジュール（src/kabusys/data）
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - market_calendar テーブルを使った営業日判定機能群を提供
        - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - DB 登録値を優先しつつ未登録日は曜日ベースでフォールバックする設計
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止
      - 夜間バッチ更新 job (calendar_update_job) を実装
        - J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）
    - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
      - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧等を保持）
      - 差分更新・バックフィル・品質チェックの設計方針を反映したインターフェース
      - ETLResult を kabusys.data.etl で再エクスポート

  - Research モジュール（src/kabusys/research）
    - ファクター計算（src/kabusys/research/factor_research.py）
      - Momentum: 1M/3M/6M リターン、200日 MA 乖離 (ma200_dev)
      - Volatility / Liquidity: 20日 ATR, 相対 ATR, 20日平均売買代金, 出来高比率
      - Value: PER（EPS が無効な場合は None）, ROE（raw_financials からの取得）
      - DuckDB SQL を用いた効率的実装（prices_daily / raw_financials のみ参照）
      - 公開関数: calc_momentum, calc_volatility, calc_value
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、入力検証あり
      - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（結合・欠損除外・最小件数チェック）
      - ランキング変換ユーティリティ（rank）: 同順位は平均ランク、丸め処理で ties の漏れ防止
      - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算
    - research パッケージ __all__ を整備し、主な関数を再エクスポート

  - 共通実装・堅牢性
    - DuckDB の取り扱いで互換性・堅牢性を考慮（空の executemany 回避、date 型変換ユーティリティ等）
    - ルックアヘッドバイアス回避設計: 各処理で datetime.today()/date.today() を直接参照せず、target_date を明示的に使用
    - OpenAI 呼び出しはテスト時に差し替え可能（モジュール内 _call_openai_api を patch 可能にしている）
    - ロギングを多用して処理状況・フォールバック・エラーを明示

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Security
- 該当なし（初回リリース）

Notes / Known limitations
- 外部サービス依存
  - OpenAI API（gpt-4o-mini）と J-Quants API クライアント（jquants_client）に依存。実行には各種 API キーや環境変数の設定が必要。
- 一部の挙動は DuckDB バージョン依存の制約（executemany 空リスト等）を考慮した実装が含まれる。
- 実稼働でのさらなる検証（特に LLM のプロンプト設計・応答バリデーション）は推奨。

--- 

参照: 各モジュールの docstring / doc コメントに処理フロー・設計方針を反映しています。