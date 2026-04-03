CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初版をリリース。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開モジュール: data, research, ai, execution, monitoring（__all__ に基づく公開）
- 環境変数／設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等を考慮した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護する protected 機能（.env.local が OS 環境変数を上書きしないよう保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視 / システム設定をプロパティ経由で取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）および必須キー取得時のエラーメッセージを実装。
- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに前日15:00 JST〜当日08:30 JST の記事を対象に OpenAI（gpt-4o-mini、JSON mode）でセンチメントを付与。
    - 1チャンク最大20銘柄のバッチ送信、1銘柄あたり記事数・文字数上限でトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code の一致、数値チェック）と ±1.0 でのクリップ。
    - 成功スコアのみ ai_scores テーブルへ置換的に保存（DELETE → INSERT、部分失敗時の既存データ保護）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計（モジュール内プライベート関数をパッチ可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
    - ETF 1321 の直近200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で market_regime に書き込み。
    - マクロニュースはニュース NLP のウィンドウ計算（calc_news_window）を利用し、マクロキーワードでフィルタ。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける）。API エラー時は macro_sentiment = 0.0 でフェイルセーフ継続。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック時のログ保護。
    - LLM 呼び出しに対するリトライ・バックオフを実装し、JSON パース不備時のフォールバックを用意。
- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で計算（ルックアヘッド回避、データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比などを計算（欠損時は None）。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を結合して PER と ROE を算出（EPS=0/欠損時は None）。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。ホライズン検証と範囲バッファ付きスキャン。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足（<3）で None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - rank: 同順位は平均ランクを与える実装（丸めによる tie 誤差対策）。
  - research パッケージは必要関数を再エクスポートして使いやすく提供。
- データ管理（kabusys.data）
  - calendar_management
    - market_calendar に基づく営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日は非営業日）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィル／健全性チェックの実装。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（fetch/save の例外ハンドリング）。
  - ETL / pipeline モジュール
    - ETLResult データクラスを作成（取得数・保存数・品質問題・エラーを集約）。
    - ETL パイプライン設計方針の実装に向けたユーティリティ（差分更新、バックフィル、品質チェック連携のための型など）。
  - etl モジュールで ETLResult を再エクスポートして公開。
- テスト・運用上の堅牢化
  - ルックアヘッドバイアス回避の方針を徹底（date.today()/datetime.today() を参照しない関数設計）。
  - DuckDB の実装依存（executemany に空リスト渡せない等）への対処（空チェックを追加）。
  - OpenAI SDK のエラー種別を考慮した細かな例外処理（RateLimitError/APIConnectionError/APITimeoutError/APIError）。

Changed
- （初版）設計ドキュメントやモジュール docstring で仕様・設計方針を明確化。各関数に詳細な docstring を追加。

Fixed
- .env パース時のエスケープ処理やインラインコメント処理の不整合を考慮した実装により、誤った値読み取りの防止。
- OpenAI レスポンスの JSON モードでも前後テキストが混入するケースを復元・パースして堅牢に処理。

Security
- 環境変数読み込み時に OS 環境変数（既存のプロセス環境）を優先・保護する仕組みを導入（.env による上書きは制限可能）。
- 必須 API キー未設定時は明確な ValueError を発生させることで初期設定不備を早期発見。

Migration / Upgrade notes
- 必須/推奨の環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション）
  - OPENAI_API_KEY（OpenAI 呼び出し：news_nlp / regime_detector で必要）
  - KABUSYS_ENV（development / paper_trading / live のいずれか）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- .env と .env.local のロード順序:
  - OS環境 > .env.local（上書き可）> .env（既存は上書きしない）
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

Notes / Known limitations
- OpenAI への呼び出しは gpt-4o-mini を想定した実装。将来的なモデル/SDK の変更により呼び出し部の調整が必要になる可能性あり。
- ai モジュールは API 呼び出し失敗時にフェイルセーフ（0.0 スコアやスキップ）で継続する設計。運用では失敗ログの監視を推奨。
- DuckDB Schema（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）に依存。初期導入時はスキーマ準備が必要。

開発チームへ
- 各種 API 呼び出し点（OpenAI / J-Quants / kabuAPI）のエラー監視とメトリクス収集を運用段階で追加することを推奨します。