Keep a Changelog
-----------------

すべての重要な変更はこのファイルに記録します。  
このプロジェクトのバージョニングは SemVer に従います。

[0.1.0] - 2026-03-28
--------------------

Added
- 初回公開リリース。
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン情報を追加（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 設定/環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込みを実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env パーサを実装。export KEY=val、引用符付き値、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティで取得可能に。
  - 環境変数の必須チェック（_require）および enum 的検証（KABUSYS_ENV, LOG_LEVEL）を追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数上限・文字数トリムを実装。
    - JSON Mode を用いた厳格なレスポンス処理と堅牢なバリデーション（不正レスポンスはスキップして継続）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分失敗に耐えるようコード単位で DELETE→INSERT を実施（トランザクション制御と ROLLBACK 対応）。
    - テスト容易化のため _call_openai_api を差し替え可能に（unittest.mock.patch 推奨）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、calc_news_window に基づくウィンドウでマクロ記事を抽出。
    - OpenAI 呼び出しは専用の内部実装を使用、API エラー時は macro_sentiment=0.0 としてフェイルセーフに継続。
    - 計算結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時に ROLLBACK）。

- リサーチ機能 (kabusys.research)
  - ファクター計算 (factor_research)
    - モメンタム: 1M/3M/6M リターン、200日 MA 乖離の計算関数 calc_momentum。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算する calc_volatility。
    - バリュー: raw_financials を用いた PER / ROE 取得 calc_value（PBR/配当利回りは未実装）。
    - いずれも DuckDB SQL を主体に実装し、(date, code) で結果を返す。

  - 特徴量探索 (feature_exploration)
    - 将来リターン計算 calc_forward_returns（デフォルト horizons=[1,5,21]）。
    - IC（Spearman）を計算する calc_ic（rank 関数を内部実装、同順位は平均ランク）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する設計。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索範囲を設定して無限ループを回避。
    - JPX カレンダー差分取得バッチ calendar_update_job を実装（J-Quants クライアント経由、バックフィル、健全性チェック）。冪等保存を想定。

  - ETL パイプライン (pipeline.py / etl)
    - 差分取得 → 保存 → 品質チェックの流れを想定した ETLResult データクラスを追加。
    - ETLResult は品質問題とエラーの集約、辞書変換 to_dict を提供。
    - _get_max_date などの内部ユーティリティを実装し、初回データロードやバックフィルをサポート。

Changed
- なし（初回リリースのため変更履歴はなし）。

Fixed
- なし（初回リリースのため修正履歴はなし）。

Notes / 実装上の留意点
- ルックアヘッドバイアス防止: 各種関数は datetime.today()/date.today() に依存しない設計（target_date を明示的に受け取る）。
- OpenAI API キー: news_nlp.score_news / regime_detector.score_regime は api_key 引数を受け取る。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出する。
- フェイルセーフ: LLM 呼び出し失敗やパース失敗は原則スキップして処理を継続（中立スコア 0.0 を使用するケースあり）。ただし DB 書き込み失敗は例外伝播（呼び出し元でハンドリング）。
- テストフレンドリネス: OpenAI 呼び出しや内部ユーティリティは差し替え可能に実装し、ユニットテストでのモックが容易。
- DuckDB 互換性: executemany に空リストが渡せないことを考慮して空チェックを行う等、DuckDB の既知の制約に配慮。

Security
- API キーは環境変数または引数で注入する設計。.env 自動ロード機能を利用する場合はファイルの取り扱いに注意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能）。

将来の作業候補（未実装/検討事項）
- strategy / execution / monitoring モジュールの実装（パッケージ API に含まれているが本リリースでは未提示のため実装済み/未実装を要確認）。
- ファクター群の追加（PBR, 配当利回り 等）。
- AI モデルの切替設定および追加的なレスポンス検証強化。
- more granular logging とメトリクス出力。

---