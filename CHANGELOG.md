# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。  
参照: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在差分なし）

## [0.1.0] - 2026-04-03

初回公開リリース。プロジェクトの主要機能群を実装しました。以下はコードベースから推測される主な追加点・設計方針・既知の制約です。

### Added
- パッケージ基礎
  - パッケージ情報を定義（src/kabusys/__init__.py: __version__ = "0.1.0", __all__ 設定）。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、CWD に依存しない探索を行う。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
  - .env パーサを実装（export 形式対応、クォート文字列のバックスラッシュエスケープ処理、インラインコメント処理）。
  - OS 環境変数を保護する仕組み（protected set を用いた上書き制御）。
  - Settings クラスを公開（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / ログ/環境モードなどのプロパティを提供）。
  - 必須環境変数未設定時に明確な例外を送出する _require 実装。
  - KABUSYS_ENV と LOG_LEVEL の検証（限定された許容値のみ許可）。
- AI モジュール（src/kabusys/ai）
  - ニュースセンチメント / 銘柄別 AI スコアリング（news_nlp.score_news）
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算（UTC 変換）を実装。
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ・記事数・文字数制限を設け、トークン爆発を抑制。
    - JSON Mode のレスポンス検証、スコアの ±1.0 クリップ、部分成功時のテーブル更新ロジック（DELETE→INSERT）を実装。
    - API の一時エラー（429・タイムアウト・ネットワーク断・5xx）に対する指数バックオフとリトライを実装。
    - テスト用フック（_call_openai_api を patch 可能）を提供。
  - 市場レジーム判定（ai.regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出しとリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management）
    - market_calendar を基に営業日判定（is_trading_day, is_sq_day）、前後の営業日取得（next_trading_day, prev_trading_day）、範囲内営業日列挙（get_trading_days）を実装。
    - DB にデータがない場合は曜日ベースのフォールバック（土日非営業日）。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存処理と健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - 差分取得 → 保存（jquants_client の save_* を想定）→ 品質チェック（quality モジュール）という ETL のインターフェース設計を実装。
    - ETLResult dataclass を公開（デバッグ/監査用の to_dict 等を実装）。
    - 差分再取得（backfill）やカレンダー先読みの定義、品質問題の収集・重大度判定を実装。
  - etl モジュールから ETLResult を再エクスポート（data.etl）。
- リサーチ／ファクター（src/kabusys/research）
  - factor_research: モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）計算を DuckDB 上の SQL ウィンドウ関数で実装。
  - feature_exploration: 将来リターン calc_forward_returns、IC（スピアマン ρ）計算 calc_ic、ランク付けユーティリティ rank、ファクター統計サマリ factor_summary を実装。pandas 等外部依存なしで純粋に標準ライブラリ + DuckDB を使用。
  - research パッケージで主要関数を再エクスポート。
- DuckDB 利用に関する互換性配慮
  - executemany に対して空リストを送らないチェック（DuckDB 0.10 の制約を考慮）。
  - 日付値処理や NULL 扱いに対する明示的な変換ユーティリティを追加。
- 設計上の重要方針（コード内ドキュメントとして明記）
  - AI 系の処理は datetime.today() / date.today() を参照しない（ルックアヘッドバイアス防止）。
  - API エラーはフェイルセーフ（スコア 0.0 で継続、部分失敗時は他データを保護）で運用を意図。
  - DB 書き込みは可能な限り冪等操作を用いる。

### Changed
- N/A（初回リリースのため特筆すべき変更履歴なし）

### Fixed
- N/A（初回リリース）

### Security
- 環境変数の上書き保護（既存の OS 環境変数を保護する設計）。
- API キー未設定時は明確な ValueError を送出し誤用を防止（OpenAI / J-Quants / kabu）。

### Known limitations / Notes
- 外部依存: OpenAI の Python SDK（OpenAI クライアント）および duckdb が必要。
- 実行前に必須環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の設定が必要。未設定時は例外が発生する。
- AI モデルは gpt-4o-mini を想定。将来のモデル変更は実装の調整が必要。
- news_nlp/regime_detector は JSON mode のレスポンスを期待しているが、LLM 出力の非標準テキストを補正する耐性（最外側の {} 抽出など）を備える一方、入力品質やモデル出力の変化による解析失敗はゼロフォールバックとなる（失敗時はスコアを生成しない/0.0）。
- jquants_client、quality モジュール、kabu ステーション API 連携部分は実行環境の実装に依存するため、環境ごとに設定と確認が必要。
- feature_exploration は外部ライブラリに依存せず実装しているため、非常に大規模データの処理では最適化や外部ツールの併用検討が必要。

---

以上。リリースに関する追加情報（インストール手順、環境変数サンプル、運用上の注意など）は別途 README にまとめることを推奨します。