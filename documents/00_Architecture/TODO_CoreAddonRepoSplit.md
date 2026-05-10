# Core / Addon 別リポジトリ化 TODO

- 目的: `KabuSys Core` を単体商品として成立させつつ、拡張機能を別商品として分離販売できる構成にする
- 背景: Note 等で `Core` と `Addon` を別有料コンテンツとして提供するため
- 方針: 先に責務境界を固定し、その後に別リポジトリへ分離する

---

## 1. 分離方針

原則:

- `Core` は単独で導入・検証・paper/live 運用まで完結する
- `Addon` が未導入・停止・未設定でも `Core` の売買フローは壊れない
- `Addon` は `Core` の内部実装ではなく公開 hook / interface にだけ依存する
- `Core` から `Addon` への import を禁止する

分離順:

1. 同一 repo 内で疎結合化
2. 公開インターフェース固定
3. 配布単位の文書化
4. 別 repo 化

---

## 2. Core に残すもの

以下は `Core` に残す。

### 2.1 実行基盤

- `src/kabusys/run_execution.py`
- `src/kabusys/run_monitoring.py`
- `scripts/start_system.py`
- `scripts/stop_system.py`
- PID / stop flag / process priority 制御

理由:

- 売買実行そのもの
- 障害時の最低限復旧導線
- paper/live 共通の運用土台

### 2.2 データ基盤

- DuckDB / SQLite スキーマ
- `prices_daily`
- `features`
- `signals`
- `signal_queue`
- `positions`
- `portfolio_performance`
- `market_calendar`
- `market_breadth`

理由:

- シグナル生成と実行に必須

### 2.3 最低限のデータ収集

- J-Quants 日次株価
- 財務
- 配当
- 決算カレンダー
- market breadth 計算

理由:

- 現行戦略の最低限入力

### 2.4 戦略本体

- Universe 定義
- 特徴量生成
- `signal_generator.py`
- regime / breadth / earnings avoidance
- position sizing
- risk based allocation
- `min_holding_days` / `max_holding_days` / trailing stop

理由:

- `Core` 商品として最小限の投資判断ロジックを提供するため

### 2.5 リスク管理

- `risk_config.yaml`
- drawdown 制御
- utilization / max_position_pct
- Kill Switch
- circuit breaker
- reconciliation

理由:

- 商品として外せない安全装置

### 2.6 基本レポート

- `pre_market_report`
- `market_close_report`
- `signal_queue_report`
- `position_reconciliation_report`
- `performance_report`
- backtest report

理由:

- `Core` 単体運用に必要な判断材料

### 2.7 paper / backtest

- `paper_trading`
- `MockBrokerClient`
- backtest engine / report

理由:

- 販売後の検証導線として必須

---

## 3. Addon に出す候補

以下は `Addon` 側へ切り出し候補。

### 3.1 AI Addon

- OpenAI ベースの news sentiment
- AI regime commentary
- quality_score の AI チューニング
- AI 対話型 strategy / factor 調整

理由:

- API キー依存
- 運用必須ではない
- 単体商品にしやすい

### 3.2 Notification Addon

- LINE 通知
- 将来の Slack / Discord / Email 通知

理由:

- Core 未導入でも売買に不要
- 外部 API 依存

### 3.3 Disclosure / Event Addon

- TDnet 収集
- EDINET 収集
- 開示分類
- disclosure event scoring

理由:

- 高機能だが Core 最低構成には不要
- 個別テーマとして販売しやすい

### 3.4 News Source Addon

- Yahoo News 追加導線
- 将来の RSS / 有料ニュース連携

理由:

- ソース追加型の拡張として独立しやすい

### 3.5 Operations UI Addon

- Streamlit 高機能ダッシュボード
- 追加監視ページ
- 高度な運用 UI

注意:

- `WebManual` ビュー自体を Core に残すかは要検討
- 最低限の read-only 監視だけ Core、強化 UI は Addon でもよい

### 3.6 Research / Premium Analytics Addon

- 高度な factor research
- targeted backtest 向け拡張 UI
- 比較分析テンプレート
- strategy lab の強化機能

理由:

- 学習用途・上級者用途として切り出しやすい

---

## 4. グレーゾーン

以下は販売設計次第で `Core` / `Addon` が揺れる。

### 4.1 Streamlit

選択肢:

- `Core` に最低限の `Home` / `WebManual` / `Signal Queue` を残す
- `Addon` に Performance / Strategy Lab / 高度な運用 UI を寄せる

推奨:

- まずは最低限を `Core`
- 強化 UI を `Addon`

### 4.2 Yahoo News

選択肢:

- `Core` に含める
- News Addon に切る

推奨:

- 売買ロジックが AI sentiment 非依存なら `Addon`
- 単なる RSS 保存だけなら `Core` でも可

### 4.3 performance report

推奨:

- 基本成績レポートは `Core`
- 比較分析や高機能可視化は `Addon`

---

## 5. 技術 TODO

### 5.1 公開インターフェース定義

- [ ] `Core` が外部に公開する extension points を列挙する
- [ ] provider / notifier / collector / dashboard page の IF を明文化する
- [ ] `Core` から `Addon` への直接 import を禁止する規約を決める

候補 IF:

- `Notifier`
- `NewsProvider`
- `DisclosureProvider`
- `DashboardPageProvider`
- `StrategyEnhancer`
- `ReportAugmenter`

### 5.2 import 境界の棚卸し

- [ ] `src/kabusys` 内で外部 API 依存箇所を列挙する
- [ ] OpenAI / LINE / TDnet / EDINET / Streamlit 強依存モジュールを一覧化する
- [ ] `Core` 起動経路から optional 機能が直接 import されていないか確認する

### 5.3 設定境界の整理

- [ ] `Core` 必須設定と `Addon` 任意設定を分離する
- [ ] `.env.example` を `core` と `addon` で説明分離する
- [ ] `validate_config` で `Addon` 未設定を warning 扱いに統一する

### 5.4 ディレクトリ設計

- [ ] `core` / `addons` の新レイアウト案を決める
- [ ] いったん monorepo 内で `src/kabusys_addons` などの暫定配置を決める
- [ ] README / docs の導線を `Core` 基準に組み直す

### 5.5 配布方式

- [ ] `Core` 配布方法を決める
- [ ] `Addon` 配布方法を決める
- [ ] private GitHub repo / zip / installer のどれを採るか決める
- [ ] バージョン互換表をどう持つか決める

---

## 6. 商品設計 TODO

### 6.1 Core 商品要件

- [ ] Core 単体で「導入 -> paper -> live」まで到達できることを保証する
- [ ] Core 単体の販売説明文を作る
- [ ] Core 単体のセットアップ手順を最短化する

### 6.2 Addon 商品要件

- [ ] Addon ごとに依存する Core 最低バージョンを定義する
- [ ] Addon ごとに「何が増えるか」を1文で説明できるようにする
- [ ] Addon ごとに無効時の fallback 動作を定義する

候補商品:

- AI Addon
- Notification Addon
- Disclosure Addon
- Operations UI Addon
- Premium Analytics Addon

### 6.3 ライセンス / サポート

- [ ] Core と Addon のライセンス方針を決める
- [ ] バグ修正の対象範囲を決める
- [ ] Core 更新で Addon が壊れた場合のサポート方針を決める

---

## 7. 実装順

推奨順:

1. `Core` / `Addon` の責務表を確定
2. `Core` 公開 IF を設計
3. optional 機能の import 境界を整理
4. 同一 repo 内で擬似分離
5. docs / setup / validate_config を `Core` 基準に整理
6. Addon 単位で別 repo 化

---

## 8. 最初の分離対象

最初に切り出す候補:

1. AI Addon
2. Notification Addon
3. Disclosure Addon

理由:

- Core 売買フローとの結合が比較的弱い
- 外部 API 依存が明確
- 商品として説明しやすい

Streamlit UI はその次でよい。現時点では運用導線でも使っているため、先に切ると Core 体験を痩せさせやすい。

---

## 9. 関連

- `documents/Archive/TODO_Decoupling_CoreAndExtensions.md`
- `documents/WebManual/B_CoreSetup.md`
- `documents/08_Operations/Monitoring.md`

---

## 10. Phase 1 Issue Breakdown

Phase 1 の目的は、別 repo 化そのものではなく、`Core` と `Addon` の境界を壊れない形で確定すること。

### Issue 1: Core / Addon 責務表の確定

目的:

- どの機能を `Core` に残し、どの機能を `Addon` に出すかを固定する

作業:

- [ ] 現行機能一覧を `Core` / `Addon` / `Gray Zone` に分類する
- [ ] 各機能に「なぜ Core か / なぜ Addon か」の理由を付ける
- [ ] `Streamlit`, `Yahoo News`, `performance report` の扱いを暫定決定する

完了条件:

- 責務表が 1 枚で読める
- 今後の実装判断で迷わない粒度まで落ちている

成果物候補:

- `documents/00_Architecture/TODO_CoreAddonResponsibilityMatrix.md`

### Issue 2: Core 公開インターフェース一覧の定義

目的:

- `Addon` が `Core` のどこに接続してよいかを固定する

作業:

- [ ] `Notifier`
- [ ] `NewsProvider`
- [ ] `DisclosureProvider`
- [ ] `DashboardPageProvider`
- [ ] `StrategyEnhancer`
- [ ] `ReportAugmenter`

について、現行コード上の候補ポイントを洗い出す

- [ ] 「公開 IF」と「内部実装」を分ける
- [ ] `Core` から `Addon` への逆依存禁止ルールを定義する

完了条件:

- 接続点の名前・責務・入力・出力が説明できる
- Addon 側が内部実装に触れなくても済む設計になっている

成果物候補:

- `documents/00_Architecture/TODO_CoreAddonExtensionPoints.md`

### Issue 3: optional 機能の import 境界監査

目的:

- `Addon` 候補機能が `Core` 起動経路に食い込んでいないことを確認する

作業:

- [ ] `run_execution.py`
- [ ] `run_monitoring.py`
- [ ] `run_data_update.py`
- [ ] `run_feature_gen.py`
- [ ] `run_ai_analysis.py`
- [ ] `run_strategy_signal.py`
- [ ] `run_portfolio_construction.py`

から見て、optional 機能の import を列挙する

- [ ] OpenAI
- [ ] LINE
- [ ] TDnet
- [ ] EDINET
- [ ] Streamlit

依存の入り方を整理する

完了条件:

- `Core` クリティカルパス上の optional import が見える化されている
- 修正対象がファイル単位で列挙されている

成果物候補:

- `documents/00_Architecture/TODO_CoreAddonImportBoundaryAudit.md`

### Issue 4: 設定項目の Core / Addon 分離

目的:

- 設定ファイルと `.env` を商品境界に合わせる

作業:

- [ ] `Core` 必須設定一覧を作る
- [ ] `Addon` 任意設定一覧を作る
- [ ] `.env.example` の説明を再編する
- [ ] `validate_config` で warning に落とすべき項目を整理する

完了条件:

- `Core` 導入時に見る設定と `Addon` 導入時に見る設定が分離されている
- 未導入 Addon の設定欠落で `Core` がエラーにならない方針が明文化されている

成果物候補:

- `documents/01_Data/CoreAddonConfigBoundary.md`

### Issue 5: ドキュメント導線の Core 基準化

目的:

- 販売単位として `Core` だけ読んでも導入できる文書構成にする

作業:

- [ ] WebManual の導線を `Core` 基準で見直す
- [ ] `Addon` 前提の説明にラベルを付ける
- [ ] `B_CoreSetup.md` に「Core だけでどこまでできるか」を明記する
- [ ] `Addon` 導入ページは分離候補としてマーキングする

完了条件:

- Core 購入者向けの導線が単独で完結している
- Addon 未導入でも混乱しない

成果物候補:

- `documents/WebManual/INDEX.md`
- `documents/WebManual/B_CoreSetup.md`

### Issue 6: monorepo 内の暫定分離レイアウト案

目的:

- 別 repo 化の前に、同一 repo 内で分離後レイアウトを試す

作業:

- [ ] `src/kabusys` 配下の `core` / `addons` 再配置案を作る
- [ ] `src/kabusys_addons` 方式など代替案を比較する
- [ ] import path 影響を整理する
- [ ] テスト配置の分離案を作る

完了条件:

- 実装移行時の移動先が決まっている
- どの方式で別 repo 化しやすいか判断できる

成果物候補:

- `documents/00_Architecture/CoreAddonLayoutProposal.md`

---

## 11. Phase 1 実装順

推奨順:

1. Issue 1: 責務表の確定
2. Issue 2: 公開 IF 定義
3. Issue 3: import 境界監査
4. Issue 4: 設定分離
5. Issue 5: ドキュメント導線整理
6. Issue 6: 暫定レイアウト案

理由:

- 責務と IF が決まる前に repo 分離を始めると、後戻りコストが大きい
- 先に「何を残すか」を固定し、その後に「どう分けるか」を決める方が安全

---

## 12. Phase 1 完了の定義

Phase 1 完了と見なす条件:

- `Core` と `Addon` の責務境界が文書で固定されている
- `Addon` の接続点が公開 IF として定義されている
- `Core` 起動経路における optional 依存の監査結果がある
- 設定とドキュメントが `Core` 単独導入を前提に整理されている
- 次フェーズで repo 分離に着手できる
