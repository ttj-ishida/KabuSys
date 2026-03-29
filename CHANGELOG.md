# CHANGELOG

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主に以下の機能・モジュールを追加しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ = "0.1.0"。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（将来のサブモジュール配置を想定）。

- 環境変数・設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートあり/なしの扱いに差異あり）
  - 読み込み時の保護機構: OS 環境変数を protected として .env.local による上書きを制御
  - Settings クラスを提供（環境変数からアプリ設定を取得）
    - 必須設定取得時は未設定で ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値や型変換: KABUSYS_ENV（development/paper_trading/live の検証）, LOG_LEVEL の検証、データベースパスの Path 変換（duckdb/sqlite）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI 関連（kabusys.ai）
  - ニュース NLP: score_news（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信して ai_scores テーブルへ保存
    - 時間ウィンドウ計算（JST ベース → UTC で DB 比較）
    - 1チャンク最大 20 銘柄、1銘柄あたり最大記事数・文字数制限
    - JSON Mode を用いた厳密なレスポンス期待、レスポンスバリデーション実装
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ
    - フェイルセーフ設計（API 失敗時は該当チャンクをスキップ、例外は原則的に上位に伝播させない）
    - DuckDB 用の挿入処理（部分失敗時に既存スコアを保護するため、DELETE→INSERT の個別実行）
  - 市場レジーム判定: score_regime（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定
    - マクロニュース抽出はキーワードフィルタに基づくタイトル抽出
    - OpenAI 呼び出しは JSON 出力を期待し、API エラー時は macro_sentiment=0.0 にフォールバック
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施
    - ルックアヘッドバイアス防止設計（date パラメータに基づく処理、datetime.today() を参照しない）
  - テスト容易性のため、内部の OpenAI 呼び出し関数は patch 可能に実装（モジュール間で private 関数を共有しない設計）

- データ管理（kabusys.data）
  - カレンダー管理: calendar_management
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供
    - market_calendar が未取得の場合作品フォールバックで曜日ベース（平日のみ営業日）を使用
    - JPX カレンダーを J-Quants から差分取得して保存する夜間バッチ calendar_update_job を実装（バックフィル・健全性チェック付き）
    - DB 値優先・未登録日は曜日フォールバックで一貫した振る舞い
  - ETL パイプライン: pipeline
    - ETLResult データクラスを追加（ETL 実行結果の集約、品質問題とエラーの収集）
    - 差分取得／バックフィルの方針、品質チェックの集約設計を反映
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティ関数を実装
  - etl モジュール: ETLResult の再エクスポート（kabusys.data.etl）

- 研究用ユーティリティ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: PER / ROE（raw_financials からの最新値を target_date ベースで取得）
    - 全関数は DuckDB SQL を用いた実装で、外部 API に依存しない
    - データ不足時に None を返す振る舞い
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算（結合・欠損除外・3 件未満は None）
    - rank: 同順位の平均ランク処理（丸め誤差対策）
    - factor_summary: count/mean/std/min/max/median を計算
  - zscore_normalize は kabusys.data.stats から再利用し公開

### 変更 (Changed)
- （初版のため無し）

### 修正 (Fixed)
- （初版のため無し）

### 削除 (Removed)
- （初版のため無し）

### セキュリティ (Security)
- 環境変数や API キーを必須として明示的に検証する実装を追加（未設定時は ValueError を発生）。運用時は秘密情報の管理に注意してください。

### 注意事項 / 設計上の決定
- ルックアヘッドバイアス防止: AI モジュール・研究モジュールともに内部で datetime.today()/date.today() を直接参照しない設計（すべて target_date を明示的に渡す）。
- Idempotent な DB 書き込み: ai_scores / market_regime / market_calendar 等は既存行を削除してから挿入することで冪等性を確保。
- DuckDB 互換性: executemany に空リストを渡せない等の注意点に対処した実装を行っています（空リストチェックの挿入等）。
- フェイルセーフ設計: OpenAI API 失敗時や予期しないレスポンス時は例外を投げずにフェールオーバー（ゼロスコアやスキップ）する箇所があり、部分処理失敗時に他データへの影響を最小化します。
- テスト容易性: OpenAI 呼び出し部分は patch 可能に設計し、ユニットテストでの差し替えを想定しています。

---

今後の予定（例）
- strategy / execution / monitoring サブモジュールの具体実装（発注ロジック、取引実行、監視通知）
- docs の整備（使用例、運用ガイド、環境構築手順）
- 性能最適化（大規模データ処理時のチャンク/並列化戦略）

--- 

（注）上記はコードベースからの実装内容を推測してまとめた CHANGELOG です。動作や API の詳細は各モジュールの docstring / 実装を参照してください。