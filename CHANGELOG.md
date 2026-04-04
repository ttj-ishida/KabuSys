# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従い、セマンティックバージョニング (SemVer) を採用します。

- https://keepachangelog.com/ja/1.0.0/
- バージョニング方針: https://semver.org/lang/ja/

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース。

### Added
- パッケージの基本骨格を追加
  - モジュール公開: kabusys パッケージ（data, strategy, execution, monitoring を __all__ として公開）
  - バージョン: 0.1.0 を設定

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートの検出は .git または pyproject.toml に基づく）
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの考慮）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数の取得時に ValueError を送出する _require ヘルパー
  - 各種設定プロパティを持つ Settings クラス（J-Quants、kabuステーション、LINE、DB パス、監視閾値、環境・ログレベル判定など）
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）

- AI: ニュース NLP と市場レジーム判定 (kabusys.ai.news_nlp, kabusys.ai.regime_detector)
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (gpt-4o-mini, JSON mode) へバッチ送信してセンチメントスコアを ai_scores テーブルへ保存
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）
    - バッチ処理 (_BATCH_SIZE=20)、1銘柄あたりの記事数・文字数上限の実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - 再試行ロジック（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）
    - レスポンス検証とスコアクリップ（±1.0）
    - DuckDB の executemany 空リスト制約へ配慮した安全な書き込み（部分成功時に既存スコアを保護する DELETE→INSERT ロジック）
    - API キー注入対応（引数または環境変数 OPENAI_API_KEY）
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップし処理継続

  - regime_detector.score_regime
    - ETF 1321 の 200日移動平均乖離 (ma200_ratio) とニュースマクロセンチメント（news_nlp のウィンドウ計算を再利用）を重み付け合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）
    - MA 偏差重み 70%、マクロ重み 30%（各種定数で調整可能）
    - OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）
    - DB へ冪等的に書き込むトランザクション処理（BEGIN / DELETE / INSERT / COMMIT、エラー時は ROLLBACK）
    - lookahead バイアス防止の設計（date 引数を受け、datetime.today() を直接参照しない）

- Data レイヤー
  - data.pipeline.ETLResult（ETL 実行結果を表す dataclass）を公開（kabusys.data.etl で再エクスポート）
    - ETL の取得数 / 保存数 / 品質問題 / エラー一覧を保持
    - has_errors / has_quality_errors プロパティ
    - to_dict によるシリアライズ（quality_issues を辞書化）

  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー管理ユーティリティを実装
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
      - calendar_update_job による J-Quants からの差分フェッチと market_calendar への冪等保存
    - DB にカレンダー情報がない場合の曜日ベースフォールバック（主に土日の除外）
    - バックフィルと健全性チェック（直近再取得 / 過度の未来日付検出の回避）
    - 最大探索日数制限で無限ループ防止

- Research レイヤー (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などの計算
    - calc_value: PER, ROE の計算（raw_financials から最新財務を取得して prices_daily と組合せ）
    - 実装は DuckDB SQL ベース。欠損/データ不足時は None を返す設計
  - feature_exploration
    - calc_forward_returns: 各ホライズン (デフォルト [1,5,21]) に対する将来リターン計算（LEAD を使用）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算
    - rank: 同順位は平均ランクで扱うランキング関数（丸めで ties を検知）
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算
  - 研究用関数群は副作用がなく DuckDB のみ参照（発注等は行わない）

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Deprecated
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- OpenAI API キーは引数で注入可能、または環境変数 OPENAI_API_KEY を用いる。キー未設定時は ValueError を送出して明示的に失敗する設計。

### Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を前提とする。API のレスポンス仕様変更やモデル差し替えは影響を受ける可能性あり。
- DuckDB のバージョン互換性に配慮した実装（executemany の空リスト回避など）を行っているが、環境により微調整が必要になる可能性がある。
- 一部計算は履歴データの量に依存し、十分なデータがない場合は None を返す（例: MA200 未満の場合等）。
- 自動 .env 読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して制御可能。

---

（以降のリリースではセクションを追加してください）