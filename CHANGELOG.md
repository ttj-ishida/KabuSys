# Changelog

すべての注目すべき変更は Keep a Changelog の形式に従って記録します。  
このファイルはパッケージの主要機能・設計方針・既知の注意点を利用者および開発者向けにまとめたものです。

文言はソースコードから推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-01
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。__version__ = 0.1.0、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定 / 設定管理（kabusys.config）
  - .env および環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト等のため）。
  - .env 解析機能の強化：
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
    - 上書き制御（override）と保護キーセット（protected）対応。
  - Settings クラスを実装しアプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境種別およびログレベルのバリデーションなどを提供。
    - 環境変数未設定時は明示的なエラー（ValueError）を投げる設計（必須設定の明確化）。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄別ニュースを集約して OpenAI（gpt-4o-mini）でセンチメント解析する score_news を実装。
  - 処理の主な特徴：
    - JST ベースのタイムウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して DB をクエリ。
    - 銘柄ごとに最新記事を最大数/文字数でトリムしてプロンプト化。
    - 1 API 呼び出しで最大 _BATCH_SIZE（20）銘柄を処理するチャンク処理。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフによるリトライ。
    - レスポンスの厳密な検証（JSON パース、results リスト、code と score の型検証、スコアのクリップ）。
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）して、部分失敗時にも既存データを保護。
    - テスト容易性のため OpenAI 呼び出しは差し替え可能（内部関数で patch を想定）。
- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定する score_regime を実装。
  - 主な特徴：
    - DuckDB の prices_daily と raw_news を参照して計算（ルックアヘッド防止のため target_date 未満のみ参照）。
    - マクロニュースはキーワードベースで抽出し、OpenAI に JSON 出力を要求して macro_sentiment を取得。
    - OpenAI API の失敗時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - 結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
- 研究用（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M のリターンと 200 日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。ATR のデータ不足時は None。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS=0/欠損は None）と ROE を取得。
    - 設計方針として DuckDB 上の SQL と Python の組合せで計算し、外部 API や実際の売買 API へはアクセスしない実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト: 1,5,21 営業日）後の終値リターンを計算。horizons の入力検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。十分なサンプルがない場合は None を返す。
    - rank: 同順位は平均ランクとなるランク付け実装（丸め処理を前処理に行い ties の扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを返す。
  - research パッケージ __init__ から主要関数を再エクスポート。
- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未登録時は曜日ベース（土日を非営業日）でフォールバックする一貫設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新。バックフィルと健全性チェック（未来日の異常検出）を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を導入し ETL 実行結果（取得数・保存数・品質問題・エラー）を集約、to_dict で辞書化可能。
    - pipeline モジュールにおける差分更新・保存・品質チェックを想定した設計（J-Quants クライアント経由で idempotent 保存等）。
  - etl モジュールで ETLResult を再エクスポート。
- OpenAI クライアント統合
  - news_nlp と regime_detector で OpenAI Chat Completions API（gpt-4o-mini + JSON Mode）を利用する共通的な呼び出しパターンを実装。リトライやエラーハンドリングを明示。
- テスト性・堅牢性のための設計
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部ロジックで直接参照しない設計（target_date を明示的に渡す）。
  - DB 書き込みは冪等化（DELETE → INSERT、ON CONFLICT を想定）し、部分失敗時のデータ保全を考慮。
  - OpenAI 呼び出し箇所は差し替え（mock）しやすい構造。

### Changed
- 初回リリースのため該当なし（新規実装が中心）。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する形で実装。必須未設定時は明示的に ValueError を発生させることで誤設定早期検出を目指す。

### Notes / Known issues
- pipeline._get_max_date 関数の末尾に不完全な実装の痕跡があるように見えます（ソースが途中で切れている可能性）。実装の最終確認・単体テストを推奨します。
- data/__init__.py は現在空で、jquants_client 等の外部クライアント実装は別モジュール（kabusys.data.jquants_client）を前提しています。実稼働前に該当クライアントの実装・認証・テストが必要です。
- monitoring / execution / strategy サブパッケージは __all__ に含まれているものの、今回提供されたコード一覧には含まれていません。これらは別途実装されているか未実装の可能性があります。
- OpenAI API 呼び出しは外部サービスに依存するため、API 利用制限（レート・料金）やレスポンス変化に伴う動作影響に注意してください。news_nlp と regime_detector は複数のフェイルセーフ（リトライやフォールバック値）を備えていますが、運用時の監視が必要です。
- DuckDB のバージョン差異により executemany / リストバインドの挙動が異なるため、一部コード（ai_scores の DELETE/INSERT ロジックなど）は互換性を考慮した実装になっています。運用環境の DuckDB バージョンでの動作確認を推奨します。

-- end of changelog --