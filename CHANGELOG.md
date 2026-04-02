CHANGELOG
=========
すべての注目すべき変更はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠しています。

Unreleased
----------
注意事項 / 既知の問題:
- data.pipeline._get_max_date 関数の末尾が不完全（コード断片 "return date.fro"）で構文エラーとなるため、ETL パイプラインの一部処理が動作しません。修正が必要です。
- data/__init__.py が空であるため、パッケージ公開時にエクスポートの整備が必要な箇所があります（将来的に公開 API を整理予定）。
- OpenAI API 呼び出し周りはリトライ・フォールバックを備えていますが、実運用ではレート制限／コスト管理の追加対策（バッチ制御・スロットリング等）検討推奨。

[0.1.0] - 2026-04-02
-------------------
初期リリース — 基本機能の実装

Added
- パッケージ基本情報
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージレベルで主要サブパッケージを想定した __all__ を定義 (data, strategy, execution, monitoring)。

- 環境設定 / ロード
  - kabusys.config を追加:
    - .env ファイル（.env, .env.local）をプロジェクトルート基準で自動読み込みする機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースを強化（export 形式サポート、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
    - 既存 OS 環境変数を保護する protected キー集合をサポートし、.env.local は override（上書き）可能。
    - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス /監視閾値 / システム環境（env, log_level）等のプロパティを提供。値検証（有効な env/log_level のチェック）・利便性プロパティ（is_live / is_paper / is_dev）を追加。

- AI関連
  - kabusys.ai.news_nlp:
    - ニュース記事群を銘柄別に集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算する score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window で提供。
    - バッチサイズ制御、1銘柄あたりの最大記事数/文字数トリム、JSON Mode を利用したレスポンス検証、レスポンスの厳密なバリデーション＆スコアクリップ（±1.0）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）、エラー時はスキップして処理継続するフォールバック戦略を採用。
    - DuckDB 互換性を考慮した DB 書き込み (DELETE → INSERT) の冪等処理を実装。executemany に対する空パラメータチェックを追加。

  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200 比の算出、マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（JSON パース処理・リトライ・フェイルセーフ macro_sentiment=0.0）を備えた堅牢設計。
    - 判定結果を market_regime テーブルへ冪等的に書き込むトランザクション処理（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK ハンドリング）を実装。

- Data / ETL / カレンダー
  - kabusys.data.calendar_management:
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB の登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫した振る舞いを実装。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する calendar_update_job を実装。バックフィル・健全性チェック（未来日付の異常検出）を実装。

  - kabusys.data.pipeline / ETL:
    - ETLResult dataclass を実装して ETL 実行結果を構造化（取得件数・保存件数・品質問題・エラー等）。
    - ETLの設計方針に基づく差分取得、バックフィル、idempotent 保存、品質チェックの概念を導入。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得など）を追加（ただし _get_max_date に実装断片あり。Unreleased に記載の既知問題参照）。

  - DuckDB 互換性考慮:
    - information_schema を用いたテーブル存在チェックや、executemany 空リスト制約回避等の実装を追加。

- Research
  - kabusys.research パッケージを追加（ファクター研究・特徴量探索ユーティリティ）。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily のウィンドウ集計）。
    - calc_volatility: 20日 ATR・相対ATR・20日平均売買代金・出来高変化率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジック含む）。
    - 各関数はデータ不足時に None を返す一貫した方針。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon に基づく将来リターン（LEAD を使用した一括取得）。
    - calc_ic: factor と将来リターンの Spearman（ランク相関）を算出（同順位は平均ランク）。
    - rank, factor_summary: 値のランク化・統計サマリ（count/mean/std/min/max/median）を実装。
  - research パッケージの __init__ で主要関数を再公開。

Changed
- 全体的な設計上の方針として、日時関連関数は date.today()/datetime.today() を直接参照しない実装を徹底（ルックアヘッドバイアス回避）。
- OpenAI 呼び出し時に JSON mode の使用と、レスポンスパース失敗時の復元ロジック（文字列から最外の {} を抽出）を追加。

Fixed / Improved
- 環境変数パースの堅牢化（export 対応、クォート内エスケープ、インラインコメント処理）。
- OpenAI 呼び出し周りをリトライ/バックオフしてフェイルセーフな挙動に改善。5xx と非 5xx を区別したリトライ制御を実装。
- DB 書き込みを冪等にし、部分失敗時の既存データ保護（対象コードのみを DELETE → INSERT）を実装。
- DuckDB のバージョン差異に配慮した実装上のワークアラウンドを導入（list バインド・executemany 空リスト回避など）。
- ロギングを充実化（重要な分岐やフォールバック時にログ出力）。

Security
- 特記事項なし（認証情報は Settings で環境変数参照。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードをオフ可能）。

Documentation
- 各モジュールヘッダに処理フロー・設計方針・返却値の説明を充実させ、内部設計が追いやすいように記載。

Notes / Nowhere
- jquants_client（jquants API のクライアント）は参照されているが実装は本スナップショットに含まれないため、実動作には別途実装／注入が必要。
- strategy / execution / monitoring パッケージは __all__ に含まれているが、今回のコードスニペットには詳細実装が含まれていません。

今後の予定
- data.pipeline._get_max_date の修正（Unreleased の既知の問題を優先修正）。
- 単体テストの追加（特に OpenAI 呼び出し・DB 書き込み・時間窓ロジック・calendar edge cases）。
- jquants_client の実装・統合テストと、OpenAI 呼び出しに対するコスト／レート制御の追加。
- package export の整理（data/__init__.py の整備、外部公開 API の明確化）。

----- 
この CHANGELOG はコードの内容から推測して作成した想定変更履歴です。実際のコミット履歴やリリースノートがある場合はそちらに合わせて調整してください。