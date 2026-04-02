CHANGELOG
=========

すべての注目すべき変更を、このファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリース日は YYYY-MM-DD 形式で記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-02
--------------------

Added
- パッケージ初版リリース。
  - バージョン: 0.1.0 (src/kabusys/__init__.py にて定義)
- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント（スペース/タブの直前の #）等に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを公開（settings インスタンス）。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - CPU/MEMORY/DISK 閾値
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー
  - 未設定の必須環境変数は ValueError を送出して明示。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON-mode を用いて銘柄別センチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して半開区間で扱う（calc_news_window）。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄を処理。1 銘柄あたりの記事数・文字数上限でトリム。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。その他はスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 抽出・構造検証・スコア数値化・±1.0 でクリップ。部分失敗時も既存データ保護のため、取得したコードのみ置換（DELETE → INSERT）。
    - テスト容易性を考慮して OpenAI 呼び出し箇所を差し替え可能（ユニットテスト用に _call_openai_api を patch できる）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュース抽出はマクロキーワード群でフィルタ、最大 20 件まで取得。
    - OpenAI 呼び出しは retry や 5xx ハンドリングを実装。API 失敗時は macro_sentiment を 0.0 にフォールバック。
    - 最終結果は market_regime テーブルに冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - OpenAI API キーは引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError。

- データ処理 / ETL（kabusys.data）
  - ETLResult データクラス（kabusys.data.pipeline + etl 再エクスポート）
    - ETL の実行結果追跡（取得数・保存数・品質問題・エラーリストなど）を表現。
    - has_errors / has_quality_errors / to_dict 等のユーティリティを提供。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得（最終取得日ベース）、バックフィル、品質チェックの方針を実装（関数群の土台）。
    - J-Quants クライアント（jquants_client）経由での取得・保存、品質検査の組み込みを想定。
    - DuckDB を前提とするユーティリティ関数を提供（テーブル存在チェック、最大日付取得など）。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定機能と夜間バッチ更新 job を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータが存在しない場合は曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job にて J-Quants から差分取得 → 保存（ON CONFLICT 相当）を行い、バックフィルと健全性チェック（将来日付の異常検出）を実装。
    - 探索の最大範囲制限（_MAX_SEARCH_DAYS）により無限ループを防止。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR（平均 true range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う実装。
    - calc_value: raw_financials からの EPS/ROE に基づく PER・ROE を計算（EPS が 0 または欠損時は None）。target_date 以前の最新財務データを用いる。
    - 設計方針: DuckDB 接続を受け取り SQL ベースで完結。実運用の発注 API には一切アクセスしない。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL で取得。horizons の検証（1..252）を実装。
    - calc_ic: Spearman ランク相関（ランクベースの Pearson）を実装。十分なサンプル数がない場合は None。
    - rank: 同順位は平均ランクを返す実装（浮動小数の丸めで ties 検出を安定化）。
    - factor_summary: count / mean / std / min / max / median を計算する軽量統計サマリ。

Security
- なし

Changed
- なし（初版）

Fixed
- なし（初版）

Deprecated
- なし

Notes / Known limitations
- OpenAI 連携は gpt-4o-mini の JSON mode を想定しているため、将来の SDK 変更やモデル仕様変更により適宜調整が必要。
- ai モジュールは外部 API（OpenAI）呼び出しに依存するため、API キー・ネットワークの安定性が動作に影響する。ライブラリは多くのフェイルセーフとリトライを実装しているが、完全な可用性を保証するものではない。
- top-level のパッケージ公開（__all__）には strategy / execution / monitoring が含まれるが、今回提供されたコードベース内でそれらの実装ファイルは含まれていません（将来追加予定／別モジュール化の可能性あり）。
- DuckDB のバージョン互換性（executemany の空リスト扱いなど）に配慮した実装を行っていますが、実環境では使用する DuckDB バージョンでの動作確認を推奨します。

作者
- KabuSys 開発チーム

(補足) この CHANGELOG はソースコードの内容から機能・設計方針を推測して作成しています。実際のリリースノートとして使用する際は、リリース方針やコミット履歴に合わせて適宜修正してください。