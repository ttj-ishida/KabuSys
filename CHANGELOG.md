# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このリポジトリの最初のパブリックリリースを示します。

全般な方針（このリリースでの設計哲学）
- DuckDB を中心としたローカルデータプラットフォーム設計（外部発注や本番口座へのアクセスは行わないモジュール分離）。
- ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- OpenAI 呼び出しなど外部 API に対してはフェイルセーフ（API 失敗時はスコアを 0 とする、例外を抑制して処理継続）とエクスポネンシャルバックオフを採用。
- DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 等）して部分失敗時に既存データを保護。
- テスト容易性のため API キー注入や内部呼び出しのパッチ差替えポイントを用意。

[0.1.0] - 2026-04-04

Added
- パッケージの基本構成を追加
  - kabusys パッケージ初期構成（__version__ = 0.1.0）。公開 API として data, strategy, execution, monitoring を __all__ に定義。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサの実装: export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - Settings クラスを提供（J-Quants・kabu API・LINE・DB パス・監視閾値・環境・ログレベル 等の取得、必須キーのチェック）。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとに記事テキストを作成、OpenAI（gpt-4o-mini）の JSON モードでバッチ解析。
    - バッチサイズ、記事数・文字数トリム、リトライ（429/ネットワーク/タイムアウト/5xx）・バックオフを実装。
    - レスポンス検証（JSON 抽出、results 配列検証、コード一致確認、数値チェック）と ±1.0 のクリッピング。
    - ai_scores テーブルへの置換的書き込み（部分失敗時に他銘柄を保護）。
    - calc_news_window ユーティリティ（JST 基準のニュースウィンドウ計算）を提供。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードによるフィルタ）、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - LLM 呼び出しはモジュール内で独立実装し、テスト時に差し替え可能。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定（is_trading_day）、翌前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（週末を休場とする）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新（バックフィルや健全性チェックを含む）。
  - ETL パイプライン（pipeline.ETLResult と etl の再エクスポート）
    - ETL 実行結果を表す dataclass ETLResult（品質チェック結果やエラーメッセージ収集、has_errors / has_quality_errors プロパティ、辞書化メソッド）を実装。
    - pipeline モジュールの基本ユーティリティ（テーブル存在チェック、最終日取得等のユーティリティ）を実装（ETL 設計に合わせた差分取得・保存・品質チェックフローを想定）。
  - jquants_client との統合ポイント（fetch/save を呼ぶ実装場所を用意、calendar/price/financials の差分取得想定）。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算（窓内データ不足は None）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）。
    - グローバルなスキャン範囲やウィンドウバッファを定義しパフォーマンスを考慮。
  - 特徴量解析ユーティリティ（feature_exploration）
    - calc_forward_returns: 指定 horizon の将来リターンを一度のクエリで取得（ホライズン検証と上限制限あり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装（少数データは None）。
    - rank: タイ同順位を平均ランクで扱うランク変換を実装（丸め処理で ties の検出安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - data.stats との連携（zscore_normalize を再エクスポート）
- テスト支援
  - OpenAI 呼び出しや sleep 等を差し替えられるよう内部関数を分離（unittest.mock.patch による差し替え想定）。
- ロギングと警告
  - 各処理は状況に応じた INFO/DEBUG/WARNING/EXCEPTION ログを出力するよう実装。

Changed
- 初回リリースにつき変更履歴はなし。

Fixed
- 初回リリースにつき修正履歴はなし。

Notes / 注意事項
- OpenAI モデルはデフォルトで gpt-4o-mini を使用する。API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。
- .env パースは一般的なケース（export 形式、クォート、インラインコメント）に対応しているが、極端に複雑なシンタックスは未対応の可能性あり。
- DuckDB の executemany が空リストを受け付けない挙動に対する保護ロジックを含む（空の params を渡さない実装）。
- 複数箇所で「データ不足時は None / 既定値を使って継続する」設計になっているため、品質チェックや上位ロジックでの扱いに注意すること。
- strategy / execution / monitoring パッケージは __all__ に含まれるが、本リリースでは主要な実装は data / ai / research に集中しています（今後の拡張対象）。

今後の予定（短期ロードマップ）
- strategy と execution の統合（売買ロジック・発注ラッパー）の実装。
- 監視（monitoring）モジュールの拡張（プロセス管理・リソース監視の自動アクション）。
- ETL の詳細実装と品質チェック（quality モジュールの完成と統合）。
- ドキュメント補強（API リファレンス・セットアップ手順・運用ノウハウ）。

--- 

（注）この CHANGELOG は現在提供されているソースコードから推測して作成したものであり、実際のコミット履歴や外部ドキュメントに基づくものではありません。必要であれば各項目をコミット単位や実装担当者の意図に合わせて調整します。