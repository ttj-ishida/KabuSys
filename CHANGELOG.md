# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

※このリポジトリのパッケージバージョンは src/kabusys/__init__.py の __version__ を参照しています（現行: 0.1.0）。

## [0.1.0] - 2026-03-27

### Added
- 基本パッケージ初期実装を追加。
  - パッケージエントリポイント: kabusys（__all__ に data, strategy, execution, monitoring を公開）
- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（OS 環境変数を保護する保護リスト、.env.local が上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化
  - .env パーサ: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理に対応
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境判定 / ログレベル等のプロパティ）
  - 環境変数検証（許容される環境値・ログレベルの検証と例外）

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約し、銘柄別に OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
    - バッチ処理（1回最大 20 銘柄）、1 銘柄あたりの記事数・文字数制限でトークン肥大化を防止
    - JSON モードでの応答パース・冗長テキスト復元ロジック・厳密なバリデーション（結果数、コード整合性、数値チェック）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライ
    - スコアを ±1.0 にクリップし、成功分のみ ai_scores テーブルへ置換（部分失敗時に既存スコアを保護）
    - テスト容易性: OpenAI 呼び出し箇所は差し替え可能（unittest.mock.patch を想定）
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST→UTC 変換、排他ウィンドウ）
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull/neutral/bear）
    - ma200 の計算でルックアヘッド防止（target_date 未満のみ使用）
    - マクロニュース抽出（マクロキーワードによるタイトルフィルタ）
    - OpenAI 呼び出し（gpt-4o-mini）とレスポンス JSON パース、API エラー時のフォールバック macro_sentiment=0.0
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト容易性のため OpenAI 呼び出しを差し替え可能

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルの有無に依存した営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - DB 登録値がない場合は曜日ベース（週末除外）でフォールバック
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存（fetch / save を jquants_client 経由で呼出）
    - 最大探索範囲やバックフィル、将来日付サニティチェック等の安全対策を実装
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧などを保持）
    - 差分更新・バックフィル・品質チェックの設計に基づくユーティリティ実装（テーブル存在チェック、最大日付取得等）
    - J-Quants クライアントとの連携ポイントを想定（jq.fetch_* / jq.save_*）

- リサーチ/ファクター解析 (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時の None 処理）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（真のレンジ計算で NULL 伝播を制御）
    - calc_value: raw_financials と当日株価から PER / ROE を計算（EPS が無効な場合は None）
    - DuckDB を用いた SQL ベース実装（価格・財務データのみ参照、安全に本番 API を触らない）
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 複数ホライズンの将来リターンを取得（ホライズン検証、1 クエリ集約）
    - calc_ic: スピアマンランク相関による IC 計算（None 値除外・有効レコード 3 未満で None）
    - rank: 同順位は平均ランクで処理（丸めで ties 検出漏れを防止）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None 除外）
  - 研究用ユーティリティを kabusys.data.stats の zscore_normalize と併せ公開

### Changed
- （初版のため特記すべき「変更」はありません）

### Fixed
- （初版のため特記すべき「修正」はありません）

### Security
- OpenAI API キーや他の機密値は Settings 経由で取得し、必須チェックにより未設定時は明示的にエラーを出す設計（ただしソース内にキーをハードコーディングしない運用を前提）。

### Notes / Design decisions
- ルックアヘッドバイアス対策: ニューススコアリング・レジーム判定・ファクター計算などは全て target_date ベースで動作し、内部で datetime.today() / date.today() を参照しない設計。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）呼び出し失敗時は可能な限り例外を投げずフォールバック値で継続する（ログ出力を行う）。ただし DB 書き込み失敗は上位へ伝播しロールバックを試みる。
- テスト容易性: OpenAI 呼び出し箇所を差し替え可能にして単体テストを容易化（_call_openai_api をモック可能）。
- DuckDB 互換性対策: executemany に空リストを渡さない等、DuckDB の既知制約に配慮した実装。
- 未実装 / 想定事項: jquants_client など外部連携クライアントはインターフェース参照のみ（実体実装は別モジュール）。strategy / execution / monitoring パッケージは __all__ に含まれるが本差分では実装コードの出典が限定的。

--- 

今後のリリースでは、ユニットテストの追加、J-Quants 実クライアント実装の統合、strategy/execution/monitoring の具体実装と e2e テスト、ドキュメント充実（使用方法、DB スキーマ）を予定しています。