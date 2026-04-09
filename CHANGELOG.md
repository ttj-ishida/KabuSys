CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初回リリース。以下の主要機能を実装。
  - 環境設定（kabusys.config）
    - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ローダーを実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に検出。プロジェクトルートが見つからない場合はスキップ。
    - .env 行パーサは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - Settings クラスで各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス類, PAPER_FILL_MODE など）を提供し、値検証（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL）を行う。
  - ポートフォリオ構築（kabusys.portfolio）
    - 銘柄選定: select_candidates (スコア降順、同点は signal_rank でタイブレーク)。
    - 重み算出: calc_equal_weights（等分配）、calc_score_weights（スコア加重、全スコアが 0 の場合は等分配へフォールバックと警告）。
    - リスク制御: apply_sector_cap（既存保有を考慮したセクター集中制限、"unknown" セクターは除外対象にしない）。
    - レジーム乗数: calc_regime_multiplier（'bull'/'neutral'/'bear' をマッピング、未知レジームは 1.0 にフォールバックして警告）。
    - 株数算出: calc_position_sizes（allocation_method による risk_based / equal / score 対応、lot_size 単位丸め、単銘柄上限・アグリゲート上限のスケーリング、cost_buffer を用いた保守的見積もり、残差処理で lot 単位の再配分ロジック）。
  - リサーチ / ファクター計算（kabusys.research）
    - Momentum, Volatility, Value などのファクター計算を DuckDB クエリで実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（MA200 のデータ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率（必要行数が不足する場合は None）。
    - calc_value: 最新財務データ（raw_financials）を用いた PER / ROE 計算。
    - 解析補助: calc_forward_returns（複数ホライズンの将来リターンを1クエリで取得）、calc_ic（スピアマンのランク相関）、rank（同順位は平均ランク方式）、factor_summary（count/mean/std/min/max/median）。
    - 標準ライブラリと DuckDB のみで実装（pandas 等の外部依存なし）。
  - AI 関連（kabusys.ai）
    - news_nlp.score_news
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込み。
      - バッチサイズ、文字数上限、記事数上限、レスポンス検証（JSON 抽出、results リスト・型チェック・未知コード無視・数値変換）、スコアの ±1.0 クリップ。
      - リトライ（429・接続・タイムアウト・5xx）に対する指数バックオフ、失敗時は安全にスキップ。
      - 部分失敗に備え、書き込みは対象コードを限定した DELETE → INSERT の冪等処理。
    - regime_detector.score_regime
      - ETF 1321 の直近 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込み。
      - マクロ記事抽出はキーワードマッチ（複数キーワード）で最大件数を制限。LLM の失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
      - レジーム数値を合成してラベル（bull/neutral/bear）に変換し、冪等的に DB へ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しはリトライや 5xx 判定等の耐障害性を組み込み、テスト時に差し替え可能な設計（内部 _call_openai_api を patch 可能）。
  - 監視ログ永続化（kabusys.monitoring.monitoring_db）
    - SQLite ベースの監視 DB 初期化関数を実装（冪等）。system_status / trade_logs / positions / risk_logs 等のテーブルとインデックス作成を定義（スキーマ作成スクリプト）。
  - パッケージ初期化
    - __version__ = "0.1.0"、各サブパッケージのエクスポートを定義。

Fixed / Improvements
- 多くの API 呼び出し・DB 書き込みでフェイルセーフを実装（例: OpenAI API の失敗では処理継続 ＆ ログ出力、DB トランザクションでの ROLLBACK 処理の保護）。
- .env パーサの堅牢化（クォート・エスケープ・コメント解釈の改善）、OS 環境変数保護（protected set）を実装。
- DuckDB クエリはルックアヘッドバイアスを防ぐため日付条件に注意して設計（例: regime 判定で date < target_date など）。

Known issues / TODO
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過小見積りされてブロックが外れる可能性あり。将来的には前日終値や取得原価等のフォールバック導入を想定（コード内に TODO コメントあり）。
- position_sizing: 単元株（lot_size）は現状全銘柄共通の引数。将来的に銘柄別 lot_map を受け取る拡張を予定（TODO コメントあり）。
- monitoring_db のスキーマ定義はファイル末尾で続きがある可能性（提供コードが途中で切れている箇所あり）。本リリースでは主要テーブルを作成する実装を含むが、追加フィールドや制約は将来検討。

Compatibility
- DuckDB と SQLite を使用。DuckDB の executemany に関する制約（空リスト不可）を回避する実装を行っているため、古い DuckDB 互換性も考慮。
- OpenAI SDK（openai Python）に依存。テストの容易さのため API 呼び出しラッパーは差し替え可能に設計。

Acknowledgements
- ドキュメント内およびコード内に設計方針・注記（ルックアヘッドバイアス回避、フェイルセーフ、テスト置換ポイント等）を多数記載。開発・レビュー時の参照を推奨。

-----
作成: コードベース解析に基づく初回 CHANGELOG（自動生成／推定）  
必要に応じて日付・内容をプロジェクト実情に合わせて調整してください。