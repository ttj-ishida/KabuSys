# Changelog

すべての注記は Keep a Changelog の形式に従い、重要な変更点をカテゴリ別に記載しています。  
バージョン番号はパッケージ内の __version__ を参照しています。

## [0.1.0] - 2026-03-27

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージ公開: kabusys パッケージのトップレベルを定義（__all__ に data/strategy/execution/monitoring を設定）。
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイル自動ロード機能を実装（OS 環境変数優先、.env.local は上書き）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 複雑な .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境種別（development/paper_trading/live）などのプロパティを型付で取得可能。
  - 必須環境変数未設定時に ValueError を送出する _require ヘルパーを実装。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI API（gpt-4o-mini, JSON mode）へ送信し、センチメントスコア（-1.0〜1.0）を ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST 相当）を計算する calc_news_window を実装。
    - 1 銘柄あたり記事数・文字数上限（デフォルト: 最大 10 件、最大 3000 文字）や、1 API 呼び出しあたりのバッチサイズ（最大 20 銘柄）をサポート。
    - JSON レスポンスの堅牢なバリデーションとパース（前後に余計なテキストが混入した場合の復元処理を含む）を実装。
    - レートリミット・ネットワーク断・タイムアウト・5xx に対する指数バックオフによるリトライ機構を実装。API 例外やパース失敗時はフェイルセーフで該当チャンクをスキップし、全体処理は継続。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）および書き込みは「DELETE（対象コードのみ）→ INSERT」で部分失敗時のデータ保護を実現。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定する score_regime を実装。
    - マクロキーワードに基づく raw_news タイトル抽出、OpenAI（gpt-4o-mini）への JSON 出力依頼、スコア合成、冪等的な market_regime テーブル書き込みを行う。
    - API エラー時はマクロセンチメントを 0.0 として処理を継続するフェイルセーフを採用。
    - 内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
- リサーチ / ファクター（kabusys.research）
  - factor_research モジュールを追加
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離（ma200_dev）を計算。過去データ不足時に None を返す挙動。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などのボラティリティ/流動性指標を計算。NULL の取り扱いに注意した true_range 計算を実装。
    - calc_value: raw_financials から直近の財務データを取得して PER（EPS が 0/欠損時は None）・ROE を計算。
    - 全関数とも DuckDB を用いて SQL と Python の組み合わせで高速かつ再現性ある計算を実装。外部 API にはアクセスしない設計。
  - feature_exploration モジュールを追加
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算する機能。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算する実装（有効レコードが 3 未満なら None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）や基本統計量の算出ユーティリティを提供。標準ライブラリのみで実装。
- データ基盤（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。market_calendar データがない場合は曜日ベースでフォールバックする堅牢な挙動。
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants API から差分取得し冪等保存。バックフィル（直近数日を再取得）や健全性チェックを内蔵。
  - pipeline: ETL パイプライン関連を実装
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧を集約）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装上に反映（jquants_client 経由での idempotent 保存、品質問題は収集して呼び出し元に委ねる）。
  - etl を介した公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。

### Changed
- （初版のため "Changed" に該当する履歴はありません）

### Fixed
- （初版のため "Fixed" に該当する履歴はありません）

### Security
- OpenAI API キーの取り扱いは関数引数で注入可能にし、環境変数 OPENAI_API_KEY をフォールバックで使用する設計。キー未設定時は明示的に ValueError を発生させることで不意の API 呼び出しを防止。

### Notes / 実装上の注記
- DuckDB との互換性・制約（executemany に空リストを渡せない等）を考慮した実装を多数含むため、DuckDB のバージョン差異に注意して運用してください。
- AI モジュールは gpt-4o-mini（JSON Mode）を前提に設計されているため、別モデル使用や API 応答仕様の変更に伴う調整が必要になる可能性があります。
- 日時取り扱いはタイムゾーン混入を避けるため基本的に naive datetime / date を使用し、JST↔UTC の変換は明示的に実装されています（例: news ウィンドウ）。
- すべてのデータ書き込みは可能な限り冪等な操作（DELETE→INSERT、ON CONFLICT DO UPDATE など）で設計しています。部分失敗時に既存データを保護するための工夫が施されています。

---

今後のリリースでは、strategy / execution / monitoring の具体的な売買ロジックや注文実行モジュールの追加、テストカバレッジ・ドキュメントの充実、CLI やジョブスケジューラとの統合等を予定しています。必要であれば、この CHANGELOG を英語版やバージョン別の詳細化（Unreleased セクション追加等）に展開します。