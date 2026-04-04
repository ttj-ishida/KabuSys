Keep a Changelog準拠の CHANGELOG.md（日本語）を以下に作成しました。コード内容から推測した初期リリースの変更点・設計方針・重要な注意点を記載しています。

なお日付は本日時点（2026-04-04）をリリース日として記載しています。必要に応じて日付や項目を調整してください。

CHANGELOG.md
=============
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
- （今後の変更をここに記載）

[0.1.0] - 2026-04-04
--------------------
Added
- パッケージ初期リリース: kabusys
  - 公開モジュール: data, strategy, execution, monitoring（__all__ によるエクスポート）
- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に自動検出）
  - .env パーサー: export プレフィックス、クォート、エスケープ、コメント処理に対応
  - オーバーライド保護機能（OS 環境変数を保護）
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラス（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境・ログレベル検証などのプロパティ）
  - 必須環境変数未設定時は ValueError による明示的エラー

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合、OpenAI (gpt-4o-mini) を JSON mode で呼び出してセンチメントを取得
    - バッチ処理（最大 20 銘柄／リクエスト）、トークン肥大化対策（記事数上限・文字数トリム）
    - 429／ネットワーク断／タイムアウト／5xx に対する指数バックオフとリトライ
    - レスポンスの厳密バリデーション（JSON 抽出・results 構造・コード照合・数値チェック）、±1.0 でクリップ
    - 成功分のみ ai_scores テーブルへ置換（DELETE → INSERT、部分失敗時に既存データ保護）
    - API キー注入可能（引数優先、未設定時は環境変数 OPENAI_API_KEY を参照）・未指定時は ValueError

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次で regime_label を算出（bull/neutral/bear）
    - マクロニュース抽出（キーワードリスト）→ OpenAI（gpt-4o-mini）呼び出し → スコア合成・クリップ
    - OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 として継続）
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、DB 書き込み失敗時は ROLLBACK を試行して例外伝播

  - AI モジュール共通設計
    - テスト容易性のため OpenAI 呼び出し関数をモジュール内で分離し、ユニットテスト時にモック差し替え可能
    - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照せず、明示的な target_date を利用

- Research / ファクター・特徴量 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS / ROE を用いて PER / ROE を計算（PBR 等は未実装）
    - DuckDB + window 関数を用いた効率的な実装、データ不足時は None を返す設計
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得
    - calc_ic: スピアマン（ランク）相関（IC）を計算（有効レコードが 3 未満なら None）
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクで処理（丸めを用いて ties 抜けを防止）
  - kabusys.data.stats.zscore_normalize を re-export

- Data プラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定 API（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）
    - DB データ優先（未登録日は曜日ベースでフォールバック）、最大探索日数制限で無限ループ防止
    - calendar_update_job: J-Quants から差分取得 → 保存（バックフィル／健全性チェックあり）
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の構造化、品質チェック結果の辞書化）
    - ETL 処理方針を実装（差分取得、idempotent 保存、品質チェックの収集）
    - DuckDB を前提としたテーブル存在チェック／最大日付取得ユーティリティ等
  - jquants_client と連携する設計（fetch/save 関数を想定）

Changed
- 初回リリースのため該当なし（初期追加中心）

Fixed
- ルックアヘッドバイアス防止を各 AI／研究モジュールで明示的に実装（target_date による日付制御、DB クエリは date < target_date / date = target_date 等で未来データを参照しない）
- DuckDB の executemany に対する空リスト制約を考慮した安全な書き込みロジック（空チェック後に executemany 実行）

Security
- 環境変数の必須チェック（_require）により重要なキー未設定時に明示的エラーを発生
- 環境変数読み込み時に OS 環境変数を上書きしないデフォルト動作（予期しない設定上書きを防止）

Notes / Design decisions
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を使う想定で実装しているため、レスポンスの厳密な構造を期待している。実運用ではモデル／API の挙動変更に注意が必要。
- 多くの箇所でフェイルセーフ（API失敗時にスキップ・デフォルト値使用）を採用しており、部分的な失敗が全体処理を停止しないようになっている。一方で DB 書込み失敗は例外を伝播するため監視が必要。
- DuckDB を主要ストレージとして想定（ローカル分析向け）している。外部接続や別 DB を使う場合は互換性確認が必要。

開発者向け TODO（推奨）
- strategy / execution / monitoring の具象実装（現状は __all__ に記載のみ）
- J-Quants クライアント（jquants_client）の具体的実装とテストの充実
- OpenAI のレスポンス仕様や料金対策（レート制限回避、キャッシュ等）の検討
- 単体テスト・統合テストの追加（特に外部 API のモック化を前提にしたテスト）

以上。必要があれば日付や表現、追加の変更カテゴリ（Deprecated, Removed 等）を含めて調整します。